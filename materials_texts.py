"""Experiment 49 (loop.md 28.1, 28.4): a dated, open materials-science teaching corpus for retrieval ("textbook RAG").

Every passage is dated on or before 2023-12-31 (every test paper is from 2024-01-01 or later), and its text is the
dated version itself, not today's page:
  doitpoms    DoITPoMS teaching and learning packages, University of Cambridge (CC BY-NC-SA 2.0 UK): each page's
              latest Internet Archive (Wayback Machine) capture on or before 2023-12-31, dated by the capture
  mit_ocw     MIT OpenCourseWare lecture notes of materials courses taught 2005-2013 (CC BY-NC-SA 4.0): the PDFs as
              archived on or before 2023-12-31 (the old OCW URL layout), dated by the capture
  libretexts  LibreTexts "Supplemental Modules (Materials Science)" (CC BY-NC-SA): captures as for DoITPoMS
  wikipedia   materials-science articles at their last revision on or before 2023-12-31 (CC BY-SA 4.0)
A page without such a capture or revision is dropped; a build fails if any passage lacks a date on or before
2023-12-31. In addition, every passage that mentions high-entropy, medium-entropy, multi-principal-element or
compositionally complex alloys is dropped, so the corpus supplies fundamentals only.

The downloaded corpus is a cache (not committed); sources.json (URLs, captures, revision IDs, licences, counts) is
committed so the corpus can be rebuilt.

    ./.venv/bin/python materials_texts.py build [--source S ...]
    ./.venv/bin/python materials_texts.py stats
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "experiments" / "high_temperature_hea_qwen35b" / "materials_texts"
SOURCES = OUT / "sources.json"
UA = "MatHG-research/1.0 (materials-hypothesis-generation; non-commercial research)"
MAX_CHARS = 1600
MIN_CHARS = 200
WIKI_PIN = "2023-12-31T23:59:59Z"
HEA = re.compile(r"high[\s-]*entropy|medium[\s-]*entropy|multi[\s-]*principal|multiprincipal|complex[\s-]+concentrated"
                 r"|compositionally[\s-]+complex|\b(?:R?HEAs?|MEAs?|MPEAs?|CCAs?)\b|cantor\s+alloy|CoCrFeMnNi|CrMnFeCoNi"
                 r"|FeCoNiCrMn|AlCoCrFeNi", re.I)
LICENCES = {"doitpoms": "CC BY-NC-SA 2.0 UK", "mit_ocw": "CC BY-NC-SA 4.0", "libretexts": "CC BY-NC-SA 3.0 US",
            "wikipedia": "CC BY-SA 4.0"}
DOITPOMS_SKIP = {"aims", "prereqs", "questions", "links", "credits", "index_old", "further", "references", "feedback",
                 "printall"}
OCW_COURSES = ("3-40j-physical-metallurgy-fall-2009", "3-032-mechanical-behavior-of-materials-fall-2007",
               "3-205-thermodynamics-and-kinetics-of-materials-fall-2006",
               "3-012-fundamentals-of-materials-science-fall-2005", "3-044-materials-processing-spring-2013",
               "3-22-mechanical-behavior-of-materials-spring-2008")
LIBRETEXTS_ROOT = "https://eng.libretexts.org/Bookshelves/Materials_Science/Supplemental_Modules_(Materials_Science)"
WIKIPEDIA = (
    # deformation and strengthening
    "Dislocation", "Slip (materials science)", "Peierls stress", "Cross slip", "Dislocation creep", "Work hardening",
    "Solid solution strengthening", "Precipitation hardening", "Grain boundary strengthening", "Orowan mechanism",
    "Dispersion strengthening", "Oxide dispersion strengthened alloy", "Strengthening mechanisms of materials",
    "Stacking-fault energy", "Stacking fault", "Deformation twinning", "Crystal twinning", "Twinning-induced plasticity",
    "Transformation-induced plasticity", "Ductility", "Fracture toughness", "Brittle–ductile transition",
    "Ductile–brittle transition temperature", "Yield (engineering)", "Hall–Petch relationship", "Serration (alloys)",
    "Dynamic strain aging", "Portevin–Le Chatelier effect", "Lomer–Cottrell junction", "Frank–Read source",
    "Burgers vector", "Cottrell atmosphere", "Strain hardening exponent", "Superplasticity", "Fatigue (material)",
    "Thermomechanical fatigue", "Fracture mechanics", "Hydrogen embrittlement", "Temper embrittlement",
    # high temperature
    "Creep (deformation)", "Larson–Miller relation", "Diffusion creep", "Coble creep", "Nabarro–Herring creep",
    "Grain boundary sliding", "Superalloy", "Single crystal superalloy", "Gamma prime", "Rafting (metallurgy)",
    "Refractory metals", "Refractory", "Thermal barrier coating", "Oxidation", "High-temperature corrosion",
    "Hot corrosion", "Passivation (chemistry)", "Pilling–Bedworth ratio", "Wagner theory of oxidation",
    "Aluminide", "Silicide", "Pesting", "Environmental barrier coating", "Thermal expansion", "Melting point",
    "Homologous temperature", "Thermal conductivity",
    # phases and thermodynamics
    "Phase diagram", "CALPHAD", "Hume-Rothery rules", "Solid solution", "Intermetallic", "Laves phase",
    "Sigma phase", "Ordered alloy", "Order and disorder", "Spinodal decomposition", "Eutectic system",
    "Eutectoid", "Gibbs free energy", "Configurational entropy", "Enthalpy of mixing", "Lever rule",
    "Nucleation", "Classical nucleation theory", "Ostwald ripening", "Coherence (physics)",
    "Body-centered cubic", "Face-centered cubic", "Hexagonal crystal family", "Close-packing of equal spheres",
    "Valence electron concentration", "Lattice constant", "Vegard's law", "Atomic radius",
    "Short-range order", "Phase transformation", "Martensite", "Martensitic transformation", "Bainite",
    "Allotropy",
    # diffusion and kinetics
    "Diffusion", "Fick's laws of diffusion", "Kirkendall effect", "Arrhenius equation", "Activation energy",
    "Vacancy defect", "Interstitial defect", "Grain boundary", "Grain growth", "Recrystallization (metallurgy)",
    "Recovery (metallurgy)", "Zener pinning", "Texture (crystalline)", "Electron backscatter diffraction",
    # processing
    "Annealing (materials science)", "Heat treating", "Solution treatment", "Quenching", "Tempering (metallurgy)",
    "Age hardening", "Cold working", "Hot working", "Rolling (metalworking)", "Forging", "Arc melting",
    "Vacuum arc remelting", "Powder metallurgy", "Spark plasma sintering", "Hot isostatic pressing",
    "Mechanical alloying", "Ball mill", "Additive manufacturing", "Selective laser melting",
    "Electron-beam additive manufacturing", "Directed energy deposition", "Laser cladding", "Thermal spraying",
    "Physical vapor deposition", "Magnetron sputtering", "Directional solidification", "Casting (metalworking)",
    "Segregation (materials science)", "Dendrite (metal)", "Surface engineering", "Nitriding", "Carburizing",
    "Shot peening", "Severe plastic deformation", "Equal channel angular extrusion", "High-pressure torsion",
    # materials and testing
    "Nickel", "Cobalt", "Chromium", "Tungsten", "Molybdenum", "Niobium", "Tantalum", "Vanadium", "Hafnium",
    "Zirconium", "Titanium alloy", "Titanium aluminide", "Nickel aluminide", "Inconel", "Stainless steel",
    "Maraging steel", "Tool steel", "Hardness", "Vickers hardness test", "Nanoindentation", "Tensile testing",
    "Compression (physics)", "Creep testing", "X-ray crystallography", "Transmission electron microscopy",
    "Scanning electron microscope", "Atom probe", "Density functional theory", "Molecular dynamics",
    "Wear", "Tribology", "Corrosion", "Pitting corrosion", "Galvanic corrosion", "Elastic modulus",
)

_LOCK = threading.Lock()
_LAST: dict[str, float] = {}


ARCHIVE_DELAY = 4.0  # web.archive.org refuses connections from clients faster than about 15 requests a minute


def fetch(url: str, binary: bool = False, delay: float = 0.4, retries: int = 4) -> Any:
    host = urllib.parse.urlsplit(url).netloc
    if host == "web.archive.org":
        delay, retries = max(delay, ARCHIVE_DELAY), max(retries, 6)
    for attempt in range(retries):
        with _LOCK:  # polite: at most one request per host every `delay` seconds
            wait = _LAST.get(host, 0) + delay - time.time()
            if wait > 0:
                time.sleep(wait)
            _LAST[host] = time.time()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
                data = r.read()
            return data if binary else data.decode("utf-8", errors="replace")
        except Exception as error:  # noqa: BLE001 - transient network errors are retried, then the page is skipped
            retry_after = getattr(error, "headers", None) and error.headers.get("Retry-After")
            refused = "Connection refused" in str(error) or "timed out" in str(error)
            if (getattr(error, "code", None) == 429 or refused) and attempt < retries - 1:
                time.sleep(min(120, int(retry_after) if str(retry_after or "").isdigit() else 30 * (attempt + 1)))
                continue
            if attempt == retries - 1:
                print(f"  skipped {url[:120]}: {type(error).__name__}: {str(error)[:120]}", flush=True)
                return None
            time.sleep(2 ** attempt)
    return None


class _Blocks(HTMLParser):
    """Headings, paragraphs and list items in document order; scripts, navigation, tables, figures and reference
    markers are skipped."""

    SKIP = {"script", "style", "nav", "header", "footer", "table", "figure", "sup", "noscript", "form", "button"}
    BLOCK = {"h1", "h2", "h3", "h4", "p", "li"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[tuple[str, str]] = []
        self.skip = 0
        self.tag: str | None = None
        self.buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        cls = dict(attrs).get("class") or ""
        if tag in self.SKIP or any(k in cls for k in ("navbox", "reflist", "mw-editsection", "hatnote", "infobox")):
            self.skip += 1
            self._skipped = getattr(self, "_skipped", []) + [tag]
        elif tag in self.BLOCK and not self.skip:
            self._flush()
            self.tag = tag

    def handle_endtag(self, tag: str) -> None:
        stack = getattr(self, "_skipped", [])
        if self.skip and stack and stack[-1] == tag:
            stack.pop()
            self.skip -= 1
        elif tag in self.BLOCK and self.tag == tag:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self.tag and not self.skip:
            self.buf.append(data)

    def _flush(self) -> None:
        if self.tag:
            text = " ".join("".join(self.buf).split())
            kind = "h" if self.tag.startswith("h") else "p"
            # navigation items and captions are short; real paragraphs are not
            if text and (kind == "h" or len(text) >= (60 if self.tag == "li" else 40)):
                self.out.append((kind, text))
        self.tag, self.buf = None, []


def blocks(html_text: str) -> list[tuple[str, str]]:
    parser = _Blocks()
    parser.feed(html_text)
    parser._flush()
    return parser.out


def between(text: str, start: str, end: str | None = None) -> str:
    """The part of a page between two markers (the main content region); the whole page if a marker is missing."""
    i = text.find(start)
    if i < 0:
        return text
    j = text.find(end, i) if end else -1
    return text[i:j] if j > 0 else text[i:]


def _title(text: str, fallback: str) -> str:
    m = re.search(r"<title>([^<]*)</title>", text, re.S)
    return " ".join(m.group(1).split()) if m else fallback


def chunk(blocks_: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """(section, text) passages of at most MAX_CHARS, split at paragraph boundaries."""
    out, section, buf = [], "", ""
    for kind, text in blocks_:
        if kind == "h":
            if len(buf) >= MIN_CHARS:
                out.append((section, buf))
            buf, section = "", text[:120]
            continue
        while len(text) > MAX_CHARS:
            cut = text.rfind(". ", 0, MAX_CHARS) + 1 or MAX_CHARS
            if buf:
                out.append((section, buf))
                buf = ""
            out.append((section, text[:cut].strip()))
            text = text[cut:].strip()
        if len(buf) + len(text) + 1 > MAX_CHARS:
            out.append((section, buf))
            buf = ""
        buf = f"{buf} {text}".strip()
    if len(buf) >= MIN_CHARS:
        out.append((section, buf))
    return [(s, t) for s, t in out if len(t) >= MIN_CHARS]


def passages(source: str, doc_id: str, title: str, url: str, date: str | None, pieces: list[tuple[str, str]],
             counts: dict[str, int]) -> list[dict[str, Any]]:
    out = []
    for n, (section, text) in enumerate(pieces):
        if HEA.search(text) or HEA.search(section):
            counts["dropped_hea"] += 1
            continue
        out.append({"record_id": f"TXT::{source}::{doc_id}::{n:03d}", "source": source, "doc": doc_id,
                    "title": title, "section": section, "url": url, "date": date, "licence": LICENCES[source],
                    "text": text})
    return out


# ---------------------------------------------------------------- sources

# ---------------------------------------------------------------- dated snapshots (loop.md 28.4)

SNAPSHOT_BEFORE = "20231231"  # the latest Wayback Machine capture on or before 2023-12-31 (every test paper is later)
CDX = "https://web.archive.org/cdx/search/cdx?"


def _norm_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    host = parts.netloc.lower().split(":")[0].removeprefix("www.")
    return f"{host}{urllib.parse.unquote(parts.path)}".rstrip("/")


def snapshots(prefix: str) -> dict[str, tuple[str, str]]:
    """Normalised URL -> (timestamp, original URL) of its latest HTTP-200 capture on or before SNAPSHOT_BEFORE, for
    every archived URL under the prefix; URLs with a query string are skipped."""
    q = urllib.parse.urlencode({"url": f"{prefix}*", "to": SNAPSHOT_BEFORE, "output": "json",
                                "filter": "statuscode:200", "fl": "timestamp,original"})
    raw = fetch(CDX + q, delay=1.5, retries=6)
    rows = json.loads(raw)[1:] if raw and raw.strip().startswith("[") else []
    out: dict[str, tuple[str, str]] = {}
    for ts, original in rows:
        if "?" in original:
            continue
        key = _norm_url(original)
        if key not in out or ts > out[key][0]:
            out[key] = (ts, original)
    return out


def snapshot_url(ts: str, original: str) -> str:
    return f"https://web.archive.org/web/{ts}id_/{original}"  # id_: the archived bytes, without the Wayback frame


def snapshot_date(ts: str) -> str:
    return f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"


def doitpoms(counts: dict[str, int]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Every teaching package's pages as archived on or before 2023-12-31 (packages without captures are dropped)."""
    index = fetch("https://www.doitpoms.ac.uk/tlplib/index.php") or ""  # discovery only; no text is taken from it
    tlps = sorted(set(re.findall(r'href="/tlplib/([^"/]+)/index\.php"', index)))
    docs, recs = [], []

    def one(tlp: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        snaps = snapshots(f"doitpoms.ac.uk/tlplib/{tlp}/")
        pages = {}
        for key, (ts, original) in snaps.items():
            m = re.search(rf"/tlplib/{re.escape(tlp)}/([a-z0-9_\-]+)\.php$", key)
            if m and m.group(1) not in DOITPOMS_SKIP:
                pages[m.group(1)] = (ts, original)
        if not pages:
            counts["undated_dropped_documents"] += 1
            return None, []
        out, title = [], tlp
        for page, (ts, original) in sorted(pages.items())[:40]:
            raw = fetch(snapshot_url(ts, original), delay=1.0)
            if not raw:
                continue
            if page == "index":
                title = _title(raw, tlp).split("|")[0].replace("DoITPoMS - TLP Library", "").strip(" -") or tlp
            out += passages("doitpoms", f"{tlp}/{page}", tlp, snapshot_url(ts, original), snapshot_date(ts),
                            chunk(blocks(between(raw, 'class="col-lg-9', 'class="footer'))), counts)
        for r in out:
            r["title"] = title
        print(f"  doitpoms {tlp}: {len(pages)} archived pages, {len(out)} passages", flush=True)
        return {"doc": tlp, "title": title, "pages": len(pages), "passages": len(out),
                "snapshots": sorted({snapshot_date(ts) for ts, _ in pages.values()})}, out

    with ThreadPoolExecutor(1) as pool:  # sequential: the archive throttles parallel clients
        for doc, out in pool.map(one, tlps):
            if doc:
                docs.append(doc)
                recs += out
    return docs, recs


def mit_ocw(counts: dict[str, int]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Lecture-note PDFs as archived (old OCW URL layout) on or before 2023-12-31."""
    docs, recs = [], []
    for course in OCW_COURSES:
        year = re.search(r"(\d{4})$", course).group(1)
        snaps = snapshots(f"ocw.mit.edu/courses/materials-science-and-engineering/{course}/")
        pdfs = {k: v for k, v in snaps.items() if k.lower().endswith(".pdf") and "lecture" in k.lower()}
        n_pdf = 0
        for key, (ts, original) in sorted(pdfs.items()):
            data = fetch(snapshot_url(ts, original), binary=True, delay=1.0)
            if not data or not data.startswith(b"%PDF"):
                continue
            with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
                tmp.write(data)
                tmp.flush()
                text = subprocess.run(["pdftotext", "-layout", tmp.name, "-"], capture_output=True, text=True,
                                      timeout=120).stdout
            paras = [" ".join(p.split()) for p in re.split(r"\n\s*\n", text)]
            name = key.rsplit("/", 1)[-1]
            pieces = chunk([("h", name)] + [("p", p) for p in paras if len(p) > 40])
            recs += passages("mit_ocw", f"{course}/{name}", f"MIT {course}: {name}", snapshot_url(ts, original),
                             snapshot_date(ts), pieces, counts)
            n_pdf += 1
        docs.append({"doc": course, "course_year": year, "archived_lecture_pdfs": len(pdfs), "pdfs": n_pdf})
        print(f"  mit_ocw {course}: {len(pdfs)} archived lecture PDFs, {n_pdf} read", flush=True)
    return docs, recs


def libretexts(counts: dict[str, int], limit: int = 400) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The Materials Science supplemental modules as archived on or before 2023-12-31."""
    prefix = "eng.libretexts.org/Bookshelves/Materials_Science/Supplemental_Modules_(Materials_Science)/"
    snaps = snapshots(prefix)
    docs, recs = [], []
    for key, (ts, original) in sorted(snaps.items())[:limit]:
        if re.search(r"\.(png|jpe?g|gif|svg|pdf|css|js)$", key, re.I):
            continue
        raw = fetch(snapshot_url(ts, original), delay=1.0)
        if not raw:
            continue
        title = _title(raw, key).split(" - ")[0]
        out = passages("libretexts", key.split("Supplemental_Modules_(Materials_Science)/")[-1][:120], title,
                       snapshot_url(ts, original), snapshot_date(ts),
                       chunk(blocks(between(raw, "mt-content-container", "mt-content-footer"))), counts)
        if out:
            docs.append({"doc": title, "snapshot": snapshot_date(ts), "passages": len(out)})
            recs += out
    print(f"  libretexts: {len(snaps)} archived URLs, {len(docs)} pages with passages", flush=True)
    return docs, recs


def wikipedia(counts: dict[str, int]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    docs, recs = [], []

    def one(title: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        api = "https://en.wikipedia.org/w/api.php?"
        q = urllib.parse.urlencode({"action": "query", "prop": "revisions", "titles": title, "rvlimit": 1,
                                    "rvstart": WIKI_PIN, "rvdir": "older", "rvprop": "ids|timestamp",
                                    "redirects": 1, "format": "json"})
        meta = json.loads(fetch(api + q, delay=1.0, retries=6) or "{}")
        page = next(iter((meta.get("query") or {}).get("pages", {}).values()), {})
        rev = (page.get("revisions") or [{}])[0]
        if not rev.get("revid"):
            return None, []
        parsed = json.loads(fetch(api + urllib.parse.urlencode({"action": "parse", "oldid": rev["revid"],
                                                                 "prop": "text", "format": "json"}), delay=1.0,
                                 retries=6) or "{}")
        body = ((parsed.get("parse") or {}).get("text") or {}).get("*", "")
        if not body:
            return None, []
        pieces = [(s, t) for s, t in chunk(blocks(body))
                  if s.lower() not in ("references", "see also", "external links", "further reading", "notes")]
        name = page.get("title", title)
        url = f"https://en.wikipedia.org/w/index.php?oldid={rev['revid']}"
        out = passages("wikipedia", name.replace(" ", "_"), name, url, rev["timestamp"][:10], pieces, counts)
        print(f"  wikipedia {name}: {len(out)}", flush=True)
        return {"doc": name, "revid": rev["revid"], "timestamp": rev["timestamp"], "passages": len(out)}, out

    with ThreadPoolExecutor(1) as pool:  # Wikipedia rate-limits parallel API clients (HTTP 429)
        for doc, out in pool.map(one, WIKIPEDIA):
            if doc:
                docs.append(doc)
                recs += out
            else:
                counts["wikipedia_missing"] += 1
    return docs, recs


BUILDERS = {"doitpoms": doitpoms, "mit_ocw": mit_ocw, "libretexts": libretexts, "wikipedia": wikipedia}


def build_one(name: str) -> dict[str, Any]:
    """One source into passages_<source>.jsonl and sources_<source>.json (sources can be built in parallel)."""
    OUT.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {"dropped_hea": 0, "wikipedia_missing": 0, "undated_dropped_documents": 0}
    docs, recs = BUILDERS[name](counts)
    undated = [r for r in recs if not r.get("date") or r["date"] > "2023-12-31"]
    if undated:
        raise RuntimeError(f"{name}: {len(undated)} passages without a date on or before 2023-12-31")
    path = OUT / f"passages_{name}.jsonl"
    tmp = path.with_suffix(".jsonl.tmp")
    tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs))
    tmp.replace(path)
    info = {"licence": LICENCES[name], "documents": len(docs), "passages": len(recs),
            "dropped_hea_passages": counts["dropped_hea"],
            **({"missing_titles": counts["wikipedia_missing"], "pinned_to": WIKI_PIN} if name == "wikipedia" else {}),
            "built_at": time.strftime("%Y-%m-%d %H:%M"), "items": docs}
    (OUT / f"sources_{name}.json").write_text(json.dumps(info, indent=1, ensure_ascii=False) + "\n")
    print(name, len(docs), "documents", len(recs), "passages", counts, flush=True)
    return info


def merge() -> dict[str, Any]:
    """sources.json (committed) from the per-source manifests."""
    sources = {"rules": ("loop.md 28.1 and 28.4: every passage is the version dated on or before 2023-12-31 (Wikipedia "
                         f"revisions pinned to {WIKI_PIN}; DoITPoMS, LibreTexts and MIT OCW from Wayback Machine "
                         "captures on or before 2023-12-31); passages mentioning high-entropy / medium-entropy / "
                         "multi-principal-element / compositionally complex alloys are dropped."), "hea_pattern": HEA.pattern,
               "sources": {n: json.loads((OUT / f"sources_{n}.json").read_text()) for n in BUILDERS
                           if (OUT / f"sources_{n}.json").exists()}}
    SOURCES.write_text(json.dumps(sources, indent=1, ensure_ascii=False) + "\n")
    return sources


_CACHE: list[dict[str, Any]] | None = None


def load() -> list[dict[str, Any]]:
    global _CACHE
    if _CACHE is None:
        seen: set[str] = set()
        _CACHE = []
        for n in BUILDERS:  # identical passages (e.g. DoITPoMS "print all" pages) are kept once
            path = OUT / f"passages_{n}.jsonl"
            for line in path.read_text().splitlines() if path.exists() else []:
                record = json.loads(line)
                if record["text"] not in seen:
                    seen.add(record["text"])
                    _CACHE.append(record)
    return _CACHE


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("stage", choices=("build", "merge", "stats"))
    parser.add_argument("--source", action="append", choices=tuple(BUILDERS))
    args = parser.parse_args()
    if args.stage == "build":
        for name in args.source or list(BUILDERS):
            build_one(name)
        merge()
    elif args.stage == "merge":
        merge()
    else:
        recs = load()
        by: dict[str, int] = {}
        for r in recs:
            by[r["source"]] = by.get(r["source"], 0) + 1
        print(len(recs), by, sum(len(r["text"]) for r in recs) // 1000, "k characters")


if __name__ == "__main__":
    main()
