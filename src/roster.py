"""Load the official reference roster and reviewed pilot inclusion flag."""
import csv
from pathlib import Path

SOURCE = "https://ks87.ru/upload/iblock/0d0/g3l1e2w45f8iz59aqp5cthkj2yibgwrd.pdf"
DATA_FILE = Path(__file__).resolve().parents[1] / "date" / "settlements.csv"

with DATA_FILE.open(encoding="utf-8-sig", newline="") as stream:
    rows = list(csv.DictReader(stream))
names = [row["settlement"] for row in rows]
if (len(names) != 46 or len(set(names)) != len(names)
        or any(row["rated"] not in {"0", "1"} or row["source_id"] != "S17" for row in rows)):
    raise ValueError("The reference roster must contain 46 unique settlements")
SETTLEMENTS = set(names)
RATED = {row["settlement"] for row in rows if row["rated"] == "1"}
if len(RATED) != 37 or "Анадырь" not in RATED:
    raise ValueError("The reviewed pilot must contain 37 settlements including Anadyr")
