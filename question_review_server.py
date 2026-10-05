"""Serve a browser interface for reviewing question clusters and grounded answers."""
from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DEFAULT_ROOT = (
    Path(__file__).parent
    / "experiments/high_temperature_hea_qwen35b/question_centered"
)
STATIC_DIR = Path(__file__).parent / "question_review_interface"


def cluster_summaries(cluster_dir: Path) -> list[dict]:
    rows = []
    for path in sorted(cluster_dir.glob("question_cluster*.json")):
        payload = json.loads(path.read_text())
        rows.append({
            "cluster_id": payload["cluster_id"],
            "canonical_question": payload["canonical_question"],
            "domain": payload["facets"]["domain"],
            "subtopic": payload["facets"]["subtopic"],
            "question_count": payload["question_count"],
            "paper_count": payload["paper_count"],
            "answer_count": len(payload.get("answers", [])),
            "file": path.name,
        })
    return rows


class ReviewHandler(BaseHTTPRequestHandler):
    root: Path = DEFAULT_ROOT

    def _json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        encoded = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self._file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/api/clusters":
            query = parse_qs(parsed.query)
            domain = query.get("domain", [""])[0]
            search = query.get("search", [""])[0].casefold()
            rows = cluster_summaries(self.root / "clusters")
            if domain:
                rows = [row for row in rows if row["domain"] == domain]
            if search:
                rows = [
                    row for row in rows
                    if search in row["canonical_question"].casefold()
                    or search in row["subtopic"].casefold()
                ]
            self._json(rows)
            return
        if parsed.path.startswith("/api/cluster/"):
            filename = parsed.path.removeprefix("/api/cluster/")
            if "/" in filename or not filename.endswith(".json"):
                self.send_error(HTTPStatus.BAD_REQUEST)
                return
            self._file(
                self.root / "clusters" / filename,
                "application/json; charset=utf-8",
            )
            return
        if parsed.path == "/api/evaluation":
            self._file(
                self.root / "results" / "question_evaluation.json",
                "application/json; charset=utf-8",
            )
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8875)
    args = parser.parse_args()
    ReviewHandler.root = args.root
    server = ThreadingHTTPServer((args.host, args.port), ReviewHandler)
    print(f"Question review interface: http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
