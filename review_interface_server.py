"""Serve a side-by-side PDF and grounded role/question review interface."""
from __future__ import annotations

import argparse
import json
import mimetypes
import re
import unicodedata
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pymupdf

DEFAULT_EXPERIMENT_DIR = (
    Path(__file__).parent
    / "experiments"
    / "high_temperature_hea_qwen35b"
)
STATIC_DIR = Path(__file__).parent / "review_interface"
_SPACE_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _normalized(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text).casefold()
    return " ".join(_TOKEN_RE.findall(decomposed))


def _compact_normalized(text: str) -> str:
    return _normalized(text).replace(" ", "")


def _pdf_pages(pdf_path: Path) -> list[dict]:
    pages = []
    with pymupdf.open(pdf_path) as document:
        for page in document:
            words = []
            compact_parts = []
            offset = 0
            for raw_word in page.get_text("words", sort=True):
                token = _compact_normalized(str(raw_word[4]))
                if not token:
                    continue
                words.append({
                    "rect": tuple(float(value) for value in raw_word[:4]),
                    "block": int(raw_word[5]),
                    "line": int(raw_word[6]),
                    "start": offset,
                    "end": offset + len(token),
                })
                compact_parts.append(token)
                offset += len(token)
            pages.append({
                "width": float(page.rect.width),
                "height": float(page.rect.height),
                "compact": "".join(compact_parts),
                "normalized": _normalized(page.get_text("text")),
                "words": words,
            })
    return pages


def _rectangles_for_span(page: dict, span: str) -> list[dict[str, float]]:
    compact_span = _compact_normalized(span)
    start = page["compact"].find(compact_span)
    if start < 0 or not compact_span:
        return []
    end = start + len(compact_span)
    matched = [
        word for word in page["words"]
        if word["end"] > start and word["start"] < end
    ]
    rectangles = []
    current = None
    for word in matched:
        x0, y0, x1, y1 = word["rect"]
        line_key = (word["block"], word["line"])
        if current and current["line_key"] == line_key:
            current["x1"] = max(current["x1"], x1)
            current["y0"] = min(current["y0"], y0)
            current["y1"] = max(current["y1"], y1)
            continue
        current = {
            "line_key": line_key,
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,
        }
        rectangles.append(current)
    return [
        {
            "x": rectangle["x0"],
            "y": rectangle["y0"],
            "width": rectangle["x1"] - rectangle["x0"],
            "height": rectangle["y1"] - rectangle["y0"],
        }
        for rectangle in rectangles
    ]


def _pdf_matches_from_pages(pages: list[dict], spans: list[str]) -> list[dict]:
    matches_by_page: dict[int, dict] = {}
    for span_index, span in enumerate(spans):
        for page_index, page in enumerate(pages):
            rectangles = _rectangles_for_span(page, span)
            if not rectangles:
                continue
            match = matches_by_page.setdefault(page_index + 1, {
                "page": page_index + 1,
                "page_width": page["width"],
                "page_height": page["height"],
                "highlights": [],
            })
            for rectangle in rectangles:
                match["highlights"].append({
                    **rectangle,
                    "span_index": span_index,
                })
            break
    return list(matches_by_page.values())


def _find_pdf_matches(pdf_path: Path, spans: list[str]) -> list[dict]:
    return _pdf_matches_from_pages(_pdf_pages(pdf_path), spans)


def _evidence_context(source_text: str, span: str, padding: int = 420) -> dict[str, str]:
    start = source_text.find(span)
    if start < 0:
        return {"before": "", "highlight": span, "after": "", "grounded": False}
    end = start + len(span)
    before_start = max(0, start - padding)
    after_end = min(len(source_text), end + padding)
    return {
        "before": _SPACE_RE.sub(" ", source_text[before_start:start]).strip(),
        "highlight": span,
        "after": _SPACE_RE.sub(" ", source_text[end:after_end]).strip(),
        "grounded": True,
    }


def _find_pdf_page(pdf_path: Path, spans: list[str]) -> int | None:
    if not spans:
        return None
    normalized_spans = [_normalized(span) for span in spans if _normalized(span)]
    if not normalized_spans:
        return None
    best_page: int | None = None
    best_score = 0.0
    with pymupdf.open(pdf_path) as document:
        for page_index, page in enumerate(document):
            page_text = _normalized(page.get_text("text"))
            compact_page_text = page_text.replace(" ", "")
            if any(span.replace(" ", "") in compact_page_text for span in normalized_spans):
                return page_index + 1
            page_tokens = set(page_text.split())
            for span in normalized_spans:
                tokens = set(span.split())
                score = len(tokens & page_tokens) / max(len(tokens), 1)
                if score > best_score:
                    best_score = score
                    best_page = page_index + 1
    return best_page if best_score >= 0.6 else None


class ReviewData:
    def __init__(self, experiment_dir: Path):
        self.experiment_dir = experiment_dir.resolve()
        self.papers_dir = self.experiment_dir / "outputs" / "papers"
        self.text_dir = self.experiment_dir / "data" / "corpus" / "text"
        if not self.papers_dir.is_dir():
            raise FileNotFoundError(f"paper outputs directory not found: {self.papers_dir}")
        self._pdf_pages_cache: dict[str, list[dict]] = {}

    def paper_ids(self) -> list[str]:
        return sorted(path.name for path in self.papers_dir.iterdir() if path.is_dir())

    def paper_dir(self, paper_id: str) -> Path:
        if paper_id not in self.paper_ids():
            raise KeyError(paper_id)
        return self.papers_dir / paper_id

    def list_papers(self) -> list[dict]:
        papers = []
        for paper_id in self.paper_ids():
            root = self.papers_dir / paper_id
            metadata = json.loads((root / "metadata.json").read_text())
            roles = json.loads((root / "output" / "roles.json").read_text())
            questions = json.loads((root / "output" / "questions.json").read_text())
            role_count = sum(
                len(items) for items in roles.get("reconciled_by_role", {}).values()
            )
            papers.append({
                "paper_id": paper_id,
                "rank": metadata.get("rank"),
                "title": metadata.get("title", paper_id),
                "journal": metadata.get("journal", ""),
                "publication_year": metadata.get("publication_year"),
                "role_count": role_count,
                "question_count": len(questions.get("questions", [])),
            })
        papers.sort(key=lambda item: (item["rank"] or 10**9, item["paper_id"]))
        return papers

    def _pages_for(self, paper_id: str) -> list[dict]:
        if paper_id not in self._pdf_pages_cache:
            pdf_path = self.paper_dir(paper_id) / "input" / "article.pdf"
            self._pdf_pages_cache[paper_id] = _pdf_pages(pdf_path)
        return self._pdf_pages_cache[paper_id]

    def _pdf_evidence(self, paper_id: str, spans: list[str]) -> tuple[int | None, list[dict]]:
        pages = self._pages_for(paper_id)
        matches = _pdf_matches_from_pages(pages, spans)
        if matches:
            return matches[0]["page"], matches
        normalized_spans = [_normalized(span) for span in spans if _normalized(span)]
        best_page = None
        best_score = 0.0
        for page_index, page in enumerate(pages):
            page_tokens = set(page["normalized"].split())
            for span in normalized_spans:
                tokens = set(span.split())
                score = len(tokens & page_tokens) / max(len(tokens), 1)
                if score > best_score:
                    best_score = score
                    best_page = page_index + 1
        return (best_page if best_score >= 0.6 else None), []

    def render_pdf_page(self, paper_id: str, page_number: int) -> bytes:
        pdf_path = self.paper_dir(paper_id) / "input" / "article.pdf"
        with pymupdf.open(pdf_path) as document:
            if page_number < 1 or page_number > document.page_count:
                raise KeyError(page_number)
            page = document[page_number - 1]
            return page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False).tobytes("png")

    def paper_details(self, paper_id: str) -> dict:
        root = self.paper_dir(paper_id)
        metadata = json.loads((root / "metadata.json").read_text())
        roles_payload = json.loads((root / "output" / "roles.json").read_text())
        questions_payload = json.loads((root / "output" / "questions.json").read_text())
        source_text = (self.text_dir / f"{paper_id}.txt").read_text(
            encoding="utf-8",
            errors="ignore",
        )

        roles = []
        for role, items in roles_payload.get("reconciled_by_role", {}).items():
            for index, item in enumerate(items):
                spans = [str(span) for span in item.get("evidence_spans", [])]
                pdf_page, pdf_matches = self._pdf_evidence(paper_id, spans)
                roles.append({
                    "id": f"{role}:{index}",
                    "role": role,
                    "content": item.get("content", ""),
                    "conflicting": bool(item.get("conflicting", False)),
                    "evidence_spans": spans,
                    "contexts": [_evidence_context(source_text, span) for span in spans],
                    "pdf_page": pdf_page,
                    "pdf_matches": pdf_matches,
                })

        questions = []
        for item in questions_payload.get("questions", []):
            spans = [str(span) for span in item.get("evidence_spans", [])]
            pdf_page, pdf_matches = self._pdf_evidence(paper_id, spans)
            questions.append({
                **item,
                "contexts": [_evidence_context(source_text, span) for span in spans],
                "pdf_page": pdf_page,
                "pdf_matches": pdf_matches,
            })

        pdf_pages = self._pages_for(paper_id)
        return {
            "paper_id": paper_id,
            "metadata": metadata,
            "roles": roles,
            "questions": questions,
            "pdf_page_count": len(pdf_pages),
            "pdf_url": f"/api/papers/{paper_id}/pdf",
            "pdf_notice": (
                "The PDF is displayed only for visual review. Pipeline extraction and exact "
                "grounding use the XML-derived text."
            ),
        }


class ReviewHandler(BaseHTTPRequestHandler):
    server_version = "MatHGReview/1.0"

    @property
    def data(self) -> ReviewData:
        return self.server.review_data  # type: ignore[attr-defined]

    def _send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, body: bytes, content_type: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "private, max-age=3600")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str | None = None) -> None:
        size = path.stat().st_size
        start = 0
        end = size - 1
        status = HTTPStatus.OK
        range_header = self.headers.get("Range", "")
        range_match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header)
        if range_match:
            start_text, end_text = range_match.groups()
            if start_text:
                start = int(start_text)
            if end_text:
                end = min(int(end_text), end)
            if not start_text and end_text:
                length = min(int(end_text), size)
                start = size - length
                end = size - 1
            if start > end or start >= size:
                self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return
            status = HTTPStatus.PARTIAL_CONTENT

        content_length = end - start + 1
        self.send_response(status)
        self.send_header(
            "Content-Type",
            content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        )
        self.send_header("Content-Length", str(content_length))
        self.send_header("Accept-Ranges", "bytes")
        if status == HTTPStatus.PARTIAL_CONTENT:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with path.open("rb") as source:
            source.seek(start)
            remaining = content_length
            while remaining:
                chunk = source.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        path = unquote(urlsplit(self.path).path)
        try:
            if path == "/api/papers":
                self._send_json(self.data.list_papers())
                return
            match = re.fullmatch(r"/api/papers/(PMC\d+)", path)
            if match:
                self._send_json(self.data.paper_details(match.group(1)))
                return
            match = re.fullmatch(r"/api/papers/(PMC\d+)/pdf", path)
            if match:
                pdf = self.data.paper_dir(match.group(1)) / "input" / "article.pdf"
                self._send_file(pdf, "application/pdf")
                return
            match = re.fullmatch(r"/api/papers/(PMC\d+)/pdf/pages/(\d+)\.png", path)
            if match:
                image = self.data.render_pdf_page(match.group(1), int(match.group(2)))
                self._send_bytes(image, "image/png")
                return
            static_name = "index.html" if path == "/" else path.lstrip("/")
            static_path = (STATIC_DIR / static_name).resolve()
            if STATIC_DIR.resolve() not in static_path.parents:
                raise FileNotFoundError(path)
            self._send_file(static_path)
        except KeyError:
            self._send_json({"error": "paper not found"}, HTTPStatus.NOT_FOUND)
        except FileNotFoundError:
            self._send_json({"error": "resource not found"}, HTTPStatus.NOT_FOUND)
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as error:  # noqa: BLE001 - expose local review-server errors
            self._send_json({"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[review-interface] {self.address_string()} - {format % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-dir", type=Path, default=DEFAULT_EXPERIMENT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), ReviewHandler)
    server.review_data = ReviewData(args.experiment_dir)  # type: ignore[attr-defined]
    print(f"[review-interface] http://{args.host}:{args.port}")
    print("[review-interface] PDFs are displayed for visual inspection only.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
