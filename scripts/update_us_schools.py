"""Build the nationwide US school directory from NCES CCD/EDGE and IPEDS."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
from collections import Counter
from pathlib import Path


LEVEL_TYPES = {
    "Elementary": "Elementary School",
    "Middle": "Middle School",
    "High": "High School",
}


def clean(value):
    return (value or "").strip()


def address(*parts):
    return ", ".join(part for part in (clean(value) for value in parts) if part)


def add_ccd(records, path):
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            status = clean(row.get("UPDATED_STATUS")) or clean(row.get("SY_STATUS"))
            if status != "1":
                continue
            level = clean(row.get("LEVEL"))
            types = [LEVEL_TYPES[level]] if level in LEVEL_TYPES else []
            if not types and level == "Other":
                offered = {grade for grade in range(13) if clean(row.get(f"G_{grade}_OFFERED")) == "Yes"}
                if clean(row.get("G_KG_OFFERED")) == "Yes" or offered.intersection(range(1, 6)):
                    types.append("Elementary School")
                if offered.intersection(range(6, 9)):
                    types.append("Middle School")
                if offered.intersection(range(9, 13)):
                    types.append("High School")
            code = clean(row.get("NCESSCH"))
            name = clean(row.get("SCH_NAME"))
            if not code or not name:
                continue
            for school_type in types:
                records[(code, school_type)] = {
                    "code": code,
                    "name": name,
                    "type": school_type,
                    "city": clean(row.get("LCITY")),
                    "state": clean(row.get("LSTATE")),
                    "address": address(row.get("LSTREET1"), row.get("LCITY"), row.get("LSTATE"), row.get("LZIP")),
                    "office_code": "US-NCES",
                }


def inferred_edge_type(name):
    value = name.casefold()
    if re.search(r"\b(high|secondary)\b", value):
        return "High School"
    if re.search(r"\b(middle|junior high)\b", value):
        return "Middle School"
    if re.search(r"\b(elementary|primary)\b", value):
        return "Elementary School"
    return ""


def add_edge_supplements(records, path):
    """Backfill states absent from the preliminary CCD directory."""
    known_codes = {code for code, _school_type in records}
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        for values in csv.reader(source, delimiter="|"):
            if len(values) < 8:
                continue
            code, name, street, city, state, zipcode = values[0], values[2], values[4], values[5], values[6], values[7]
            if code in known_codes:
                continue
            school_type = inferred_edge_type(name)
            if not school_type:
                continue
            records[(code, school_type)] = {
                "code": code,
                "name": name,
                "type": school_type,
                "city": city,
                "state": state,
                "address": address(street, city, state, zipcode),
                "office_code": "US-NCES",
            }


def add_ipeds(records, path):
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            if clean(row.get("CYACTIVE")) != "1" or clean(row.get("POSTSEC")) != "1" or clean(row.get("DEGGRANT")) != "1":
                continue
            code = clean(row.get("UNITID"))
            name = clean(row.get("INSTNM"))
            if not code or not name:
                continue
            records[(f"IPEDS-{code}", "University")] = {
                "code": f"IPEDS-{code}",
                "name": name,
                "type": "University",
                "city": clean(row.get("CITY")),
                "state": clean(row.get("STABBR")),
                "address": address(row.get("ADDR"), row.get("CITY"), row.get("STABBR"), row.get("ZIP")),
                "office_code": "US-IPEDS",
            }


def build(source_dir, output):
    records = {}
    ccd_path = next((source_dir / "ccd").glob("ccd_sch_*.csv"))
    add_ccd(records, ccd_path)
    add_edge_supplements(records, source_dir / "edge" / "EDGE_GEOCODE_PUBLICSCH_2425.TXT")
    add_ipeds(records, source_dir / "ipeds" / "HD2024.csv")
    schools = sorted(records.values(), key=lambda item: (item["type"], item["state"], item["code"]))
    payload = {
        "sources": ["NCES CCD/EDGE 2024-25", "NCES IPEDS HD2024"],
        "as_of": "2024-25",
        "schools": schools,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as archive:
            archive.write(encoded)
    counts = Counter(item["type"] for item in schools)
    print(f"wrote {len(schools):,} searchable school records to {output}")
    for school_type, count in sorted(counts.items()):
        print(f"  {school_type}: {count:,}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "pybo" / "data" / "us_schools.json.gz")
    args = parser.parse_args()
    build(args.source_dir, args.output)


if __name__ == "__main__":
    main()
