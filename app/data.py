from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Dict

import json

from app.parsers import normalize_issuer_name


@dataclass
class StockInfo:
    ticker: str
    name: str
    figi: str


@lru_cache(maxsize=1)
def load_stocks() -> List[StockInfo]:
    path = Path(__file__).resolve().parent.parent / "stocks.json"
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [StockInfo(**x) for x in raw]


@lru_cache(maxsize=1)
def issuer_name_to_ticker() -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for s in load_stocks():
        key = normalize_issuer_name(s.name)
        mapping[key] = s.ticker
    return mapping


def infer_ticker(issuer_name: str) -> str:
    if not issuer_name:
        return ""
    norm = normalize_issuer_name(issuer_name)
    mapping = issuer_name_to_ticker()
    if norm in mapping:
        return mapping[norm]
    # fallback: contains
    for name_norm, ticker in mapping.items():
        if name_norm in norm or norm in name_norm:
            return ticker
    return ""
