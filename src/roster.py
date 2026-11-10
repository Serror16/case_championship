"""Load the official 2025 reference roster; population is not weighted."""
from pathlib import Path

SOURCE = "https://ks87.ru/upload/iblock/0d0/g3l1e2w45f8iz59aqp5cthkj2yibgwrd.pdf"
DATA_FILE = Path(__file__).resolve().parents[1] / "date" / "settlements_2025.txt"

names = [line.strip() for line in DATA_FILE.read_text(encoding="utf-8").splitlines()
         if line.strip() and not line.startswith("#")]
if len(names) != 46 or len(set(names)) != len(names):
    raise ValueError("The reference roster must contain 46 unique settlements")
SETTLEMENTS = set(names)
