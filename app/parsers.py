from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional, Dict

from bs4 import BeautifulSoup


def extract_visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    texts = [t.strip() for t in soup.stripped_strings]
    return "\n".join(texts)


SHARES_STRONG_RE = re.compile(
    r"количеств[оа]\s+приобретенн\w*\s+акц\w*[:\s]+([0-9][0-9\s\u00A0]*)",
    re.IGNORECASE,
)

SHARES_GENERIC_RE = re.compile(
    r"\b([0-9]{1,3}(?:[\s\u00A0][0-9]{3})+)\s*(?:шт\.?|акц\w*)",
    re.IGNORECASE,
)


def try_parse_shares_count(text: str) -> Optional[int]:
    if not text:
        return None
    m = SHARES_STRONG_RE.search(text)
    if not m:
        m = SHARES_GENERIC_RE.search(text)
    if not m:
        return None
    raw = m.group(1)
    digits_only = "".join(ch for ch in raw if ch.isdigit())
    try:
        return int(digits_only)
    except ValueError:
        return None


RUS_TEXT_DATE_RE = re.compile(
    r"(\d{1,2})\s+"
    r"(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)"
    r"\s+(\d{4})\s*г?",
    re.IGNORECASE,
)

DOTTED_DATE_RE = re.compile(r"(\d{2}\.\d{2}\.\d{4})")

MONTH_MAP: Dict[str, int] = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}


def try_parse_first_russian_date(text: str) -> Optional[date]:
    if not text:
        return None
    m = RUS_TEXT_DATE_RE.search(text)
    if m:
        day_s, month_s, year_s = m.groups()
        try:
            day = int(day_s)
            year = int(year_s)
            month = MONTH_MAP.get(month_s.lower())
            if month:
                return date(year, month, day)
        except Exception:
            pass
    m2 = DOTTED_DATE_RE.search(text)
    if m2:
        part = m2.group(1)
        try:
            dt = datetime.strptime(part, "%d.%m.%Y").date()
            return dt
        except Exception:
            pass
    return None


def normalize_issuer_name(name: str) -> str:
    return (
        name.replace("«", "")
        .replace("»", "")
        .replace('"', "")
        .strip()
        .lower()
    )
