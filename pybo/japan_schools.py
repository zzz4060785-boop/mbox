"""Search the local nationwide Japanese school-code dataset."""

from __future__ import annotations

import gzip
import json
import unicodedata
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).with_name("data") / "japan_schools.json.gz"

TYPE_MAPPING = {
    "초등학교": "小学校", "중학교": "中学校", "고등학교": "高等学校", "대학교": "大学",
    "小学校": "小学校", "中学校": "中学校", "高等学校": "高等学校", "大学": "大学",
}
TYPE_KO = {"小学校": "초등학교", "中学校": "중학교", "高等学校": "고등학교", "大学": "대학교"}


def _normalized(value: str) -> str:
    return unicodedata.normalize("NFKC", value or "").casefold().strip()


@lru_cache(maxsize=1)
def load_japan_schools() -> tuple[dict, ...]:
    """Load the generated MEXT dataset once per application process."""
    try:
        with gzip.open(DATA_FILE, "rt", encoding="utf-8") as source:
            payload = json.load(source)
    except (OSError, ValueError):
        return ()
    schools = payload.get("schools", []) if isinstance(payload, dict) else []
    return tuple(school for school in schools if isinstance(school, dict))


def search_japan_schools(keyword, requested_type=None):
    """Search Japanese schools by name, prefecture, address, or MEXT code."""
    query = _normalized(keyword)
    if not query:
        return []
    target_type = TYPE_MAPPING.get(requested_type)
    requested_in_japanese = requested_type in TYPE_KO
    matched = []
    for school in load_japan_schools():
        school_type = school.get("type", "")
        if target_type and school_type != target_type:
            continue
        searchable = " ".join(str(school.get(field, "")) for field in ("name", "prefecture", "address", "code"))
        if query not in _normalized(searchable):
            continue
        matched.append({
            "name": school.get("name", ""),
            "type": school_type if requested_in_japanese else TYPE_KO.get(school_type, school_type),
            "code": school.get("code", ""),
            "office_code": "JP-MEXT",
            "address": school.get("address", ""),
        })
        if len(matched) >= 30:
            break
    return matched
