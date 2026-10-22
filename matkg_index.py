"""Temporally filtered index over the MatKG per-DOI entity table.

MatKG (CC BY 4.0) mines materials entities from paper abstracts. Each row links an entity mention to the
DOI of the paper it came from and to that paper's publication year. The co-occurrence file (SUBRELOBJ) has
no DOI or year, so it cannot be filtered by date and is not used here.

The index keeps (doi, year, entity, ner) rows in SQLite. Queries return only co-occurrence statistics from
papers published strictly before the cutoff year, and never from excluded DOIs (the held-out paper and any
paper in its work family).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sqlite3
import sys
import tarfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DEFAULT_ARCHIVE = ROOT / "matkg" / "ENTPTNERDOI.csv.tar.gz"
DEFAULT_DB = Path.home() / "matkg_index" / "entdoi.sqlite"
MAX_MATCHED_ENTITIES = 6
MAX_IN_LIST = 900


def normalize_entity(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def normalize_doi(text: str) -> str:
    value = str(text or "").strip().lower()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value)
    return value


def build_index(archive: Path, db_path: Path, batch_size: int = 200_000) -> dict[str, Any]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = db_path.with_name(db_path.stem + ".building.sqlite")
    if tmp_path.exists():
        tmp_path.unlink()
    con = sqlite3.connect(tmp_path)
    con.execute("PRAGMA journal_mode=OFF")
    con.execute("PRAGMA synchronous=OFF")
    con.execute("CREATE TABLE ent (doi TEXT NOT NULL, year INTEGER NOT NULL, entity TEXT NOT NULL, ner TEXT)")
    rows = loaded = skipped = 0
    batch: list[tuple[str, int, str, str]] = []
    with tarfile.open(archive, "r:gz") as tar:
        member = next(m for m in tar.getmembers() if m.name.endswith(".csv"))
        stream = io.TextIOWrapper(tar.extractfile(member), encoding="utf-8", errors="replace", newline="")
        reader = csv.reader(stream)
        header = next(reader)
        col = {name: index for index, name in enumerate(header)}
        for row in reader:
            rows += 1
            if len(row) < len(header):
                skipped += 1
                continue
            doi = normalize_doi(row[col["DOI"]])
            entity = normalize_entity(row[col["Preferred_Entity"]] or row[col["Entity"]])
            try:
                year = int(float(row[col["Year"]]))
            except ValueError:
                year = 0
            if not doi or not entity or year <= 0:
                skipped += 1
                continue
            batch.append((doi, year, entity, row[col["NER_Tag"]]))
            loaded += 1
            if len(batch) >= batch_size:
                con.executemany("INSERT INTO ent VALUES (?, ?, ?, ?)", batch)
                batch.clear()
            if rows % 5_000_000 == 0:
                print(f"[matkg-index] rows={rows:,} loaded={loaded:,}", file=sys.stderr, flush=True)
    if batch:
        con.executemany("INSERT INTO ent VALUES (?, ?, ?, ?)", batch)
    con.execute("CREATE INDEX ent_entity ON ent(entity)")
    con.execute("CREATE INDEX ent_doi ON ent(doi)")
    con.commit()
    distinct_dois = con.execute("SELECT COUNT(DISTINCT doi) FROM ent").fetchone()[0]
    year_min, year_max = con.execute("SELECT MIN(year), MAX(year) FROM ent").fetchone()
    con.close()
    tmp_path.replace(db_path)
    return {"rows_read": rows, "rows_loaded": loaded, "rows_skipped": skipped,
            "distinct_dois": distinct_dois, "year_min": year_min, "year_max": year_max}


def candidate_phrases(text: str, max_words: int = 4) -> list[str]:
    tokens = re.findall(r"[a-z0-9][a-z0-9\-\+\.]*", str(text or "").lower())
    phrases: set[str] = set()
    for size in range(1, max_words + 1):
        for start in range(len(tokens) - size + 1):
            phrase = " ".join(tokens[start:start + size]).strip(".-+")
            if phrase:
                phrases.add(phrase)
    return sorted(phrases, key=lambda value: (-len(value), value))


def _in_clause(values: list[str]) -> str:
    return ",".join("?" * len(values))


class TemporalKG:
    """Read-only, cutoff-filtered view of the MatKG index for one held-out case."""

    def __init__(self, db_path: Path, cutoff: str, excluded_dois: set[str]) -> None:
        self.con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        self.cutoff = cutoff
        self.cutoff_year = int(cutoff[:4])
        self.excluded = sorted({normalize_doi(doi) for doi in excluded_dois if doi})

    def close(self) -> None:
        self.con.close()

    def matched_entities(self, topic: str) -> list[str]:
        phrases = candidate_phrases(topic)[:MAX_IN_LIST]
        if not phrases:
            return []
        rows = self.con.execute(
            f"SELECT entity, COUNT(DISTINCT doi) AS n FROM ent WHERE entity IN ({_in_clause(phrases)}) "
            f"AND year < ? GROUP BY entity ORDER BY n ASC, LENGTH(entity) DESC LIMIT ?",
            (*phrases, self.cutoff_year, MAX_MATCHED_ENTITIES),
        ).fetchall()
        return [entity for entity, _ in rows]

    def cooccurrences(self, topic: str, limit: int = 8, candidate_pool: int = 40) -> dict[str, Any]:
        anchors = self.matched_entities(topic)
        if not anchors:
            return {"anchors": [], "facts": []}
        exclusion = f"AND e1.doi NOT IN ({_in_clause(self.excluded)})" if self.excluded else ""
        params: list[Any] = [*anchors, self.cutoff_year, *anchors]
        if self.excluded:
            params += self.excluded
        params += [candidate_pool]
        rows = self.con.execute(
            f"SELECT e2.entity, COUNT(DISTINCT e1.doi) AS papers, MAX(e1.year) AS latest "
            f"FROM ent e1 JOIN ent e2 ON e2.doi = e1.doi "
            f"WHERE e1.entity IN ({_in_clause(anchors)}) AND e1.year < ? "
            f"AND e2.entity NOT IN ({_in_clause(anchors)}) {exclusion} "
            f"GROUP BY e2.entity ORDER BY papers DESC, e2.entity LIMIT ?",
            params,
        ).fetchall()
        if not rows:
            return {"anchors": anchors, "facts": []}
        neighbors = [neighbor for neighbor, _, _ in rows]
        neighbor_df = dict(self.con.execute(
            f"SELECT entity, COUNT(DISTINCT doi) FROM ent WHERE entity IN ({_in_clause(neighbors)}) "
            f"AND year < ? GROUP BY entity",
            (*neighbors, self.cutoff_year),
        ).fetchall())
        facts = []
        for neighbor, papers, latest in rows:
            df = max(1, int(neighbor_df.get(neighbor, papers)))
            facts.append({"neighbor": neighbor, "papers": int(papers), "latest_year": int(latest),
                          "association": round(int(papers) / df, 4)})
        facts.sort(key=lambda fact: (-fact["association"], -fact["papers"], fact["neighbor"]))
        return {"anchors": anchors, "facts": facts[:limit]}



def fact_record_id(anchors: list[str], neighbor: str) -> str:
    digest = hashlib.sha1("|".join(anchors + [neighbor]).encode("utf-8")).hexdigest()[:10]
    slug = re.sub(r"[^a-z0-9]+", "_", neighbor).strip("_")[:40] or "entity"
    return f"KG::{slug}::{digest}"


def fact_text(anchors: list[str], fact: dict[str, Any]) -> str:
    anchor_text = " / ".join(f"'{anchor}'" for anchor in anchors)
    return (f"Co-occurrence statistic from earlier materials abstracts: {anchor_text} and "
            f"'{fact['neighbor']}' are mentioned together in {fact['papers']} papers published before "
            f"the cutoff (most recent {fact['latest_year']}); {fact['association']:.0%} of papers that "
            f"mention '{fact['neighbor']}' also mention {anchor_text}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    build.add_argument("--db", type=Path, default=DEFAULT_DB)
    query = sub.add_parser("query")
    query.add_argument("--db", type=Path, default=DEFAULT_DB)
    query.add_argument("--cutoff", required=True)
    query.add_argument("--topic", required=True)
    query.add_argument("--exclude-doi", action="append", default=[])
    args = parser.parse_args()
    if args.command == "build":
        print(json.dumps(build_index(args.archive, args.db), indent=1))
    else:
        kg = TemporalKG(args.db, args.cutoff, set(args.exclude_doi))
        try:
            print(json.dumps(kg.cooccurrences(args.topic), indent=1))
        finally:
            kg.close()


if __name__ == "__main__":
    main()
