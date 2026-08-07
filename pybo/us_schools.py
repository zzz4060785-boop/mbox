"""Search the local nationwide United States school directory."""

from __future__ import annotations

import gzip
import json
import unicodedata
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).with_name("data") / "us_schools.json.gz"

TYPE_MAPPING = {
    "초등학교": "Elementary School",
    "중학교": "Middle School",
    "고등학교": "High School",
    "대학교": "University",
    "Elementary School": "Elementary School",
    "Middle School": "Middle School",
    "High School": "High School",
    "University": "University",
}
TYPE_KO = {
    "Elementary School": "초등학교",
    "Middle School": "중학교",
    "High School": "고등학교",
    "University": "대학교",
}


def _normalized(value: str) -> str:
    return unicodedata.normalize("NFKC", value or "").casefold().strip()


@lru_cache(maxsize=1)
def load_us_schools() -> tuple[dict, ...]:
    try:
        with gzip.open(DATA_FILE, "rt", encoding="utf-8") as source:
            payload = json.load(source)
    except (OSError, ValueError):
        return ()
    schools = payload.get("schools", []) if isinstance(payload, dict) else []
    return tuple(school for school in schools if isinstance(school, dict))


def search_us_schools(keyword, requested_type=None):
    """Search US schools by name, city, state, address, or NCES/IPEDS ID."""
    query = _normalized(keyword)
    if not query:
        return []
    target_type = TYPE_MAPPING.get(requested_type)
    requested_in_english = requested_type in TYPE_KO
    matched = []
    for school in load_us_schools():
        school_type = school.get("type", "")
        if target_type and school_type != target_type:
            continue
        searchable = " ".join(str(school.get(field, "")) for field in ("name", "city", "state", "address", "code"))
        if query not in _normalized(searchable):
            continue
        matched.append({
            "name": school.get("name", ""),
            "type": school_type if requested_in_english else TYPE_KO.get(school_type, school_type),
            "code": school.get("code", ""),
            "office_code": school.get("office_code", "US-NCES"),
            "address": school.get("address", ""),
        })
        if len(matched) >= 30:
            break
    return matched
