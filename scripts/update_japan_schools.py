"""Build the nationwide Japanese school search dataset from MEXT CSV files."""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import re
from collections import Counter
from pathlib import Path

PREFECTURES = (
    "", "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県",
    "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県", "新潟県", "富山県",
    "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県", "三重県",
    "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県", "鳥取県", "島根県",
    "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県", "福岡県",
    "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
)
TYPE_MAP = {
    "小学校": "小学校",
    "中学校": "中学校",
    "高校": "高等学校",
    "高等学校": "高等学校",
    "大学": "大学",
    "短期大学": "大学",
}


def read_rows(path: Path):
    text = path.read_bytes().decode("cp932")
    source = io.StringIO(text, newline="")
    reader = csv.reader(source)
    next(reader, None)
    headers = [value.replace("\r", "").replace("\n", "") for value in next(reader)]
    for values in reader:
        if not values or not any(values):
            continue
        values += [""] * (len(headers) - len(values))
        yield dict(zip(headers, values))


def build(source_dir: Path, output: Path):
    schools = {}
    for filename in ("east.csv", "west.csv", "higher.csv"):
        for row in read_rows(source_dir / filename):
            raw_type = row.get("学校種", "").strip()
            type_match = re.search(r"\(([^)]+)\)", raw_type)
            school_type = TYPE_MAP.get(type_match.group(1) if type_match else raw_type)
            if not school_type or row.get("属性情報廃止年月日", "").strip():
                continue
            code = row.get("学校コード", "").strip()
            name = row.get("学校名", "").strip()
            if not code or not name:
                continue
            try:
                pref_value = row.get("都道府県番号", "").strip()
                pref_match = re.match(r"\d+", pref_value)
                prefecture = PREFECTURES[int(pref_match.group(0))] if pref_match else ""
            except (ValueError, IndexError):
                prefecture = ""
            schools[code] = {
                "code": code, "name": name, "type": school_type, "prefecture": prefecture,
                "address": row.get("学校所在地", "").strip(),
            }
    records = sorted(schools.values(), key=lambda item: (item["type"], item["code"]))
    payload = {"source": "文部科学省 学校コード一覧", "as_of": "2026-05-01", "status": "provisional", "schools": records}
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as archive:
            archive.write(encoded)
    counts = Counter(item["type"] for item in records)
    print(f"wrote {len(records):,} schools to {output}")
    labels = {"小学校": "elementary", "中学校": "middle", "高等学校": "high", "大学": "university"}
    for school_type, count in sorted(counts.items()):
        print(f"  {labels.get(school_type, 'other')}: {count:,}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "pybo" / "data" / "japan_schools.json.gz")
    args = parser.parse_args()
    build(args.source_dir, args.output)


if __name__ == "__main__":
    main()
