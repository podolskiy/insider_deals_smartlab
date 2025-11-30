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

# Объём: 76.50 млн. рублей / 4.96 млн ₽ / 200.08 рублей / 2 тыс. руб.
VOLUME_RE = re.compile(
    r"об[ьъ]?[её]м[:\s]*"              # Объем / Обьём / Объем / ОБЪЕМ и т.п.
    r"([\d\s.,]+)"                     # число (209.60 / 4,96 / 2 000)
    r"\s*(млн\.?|тыс\.?|млрд\.?|трлн\.?)?"             # опционально: млн / тыс
    r"\s*(руб(?:лей|\.|)|₽)",         # рубли / ₽
    re.IGNORECASE,
)



def try_parse_volume_rub(text: str) -> Optional[float]:
    """
    Парсим строку вида:
    - 'Обьём:\n76.50 млн. рублей'
    - 'Объем: 4,96 млн ₽'
    - 'Объем: 200.08 рублей'
    - 'Объем: 2 тыс. руб.'
    Возвращаем сумму в рублях (float) или None.
    """
    if not text:
        return None

    m = VOLUME_RE.search(text)
    if not m:
        return None

    raw_num, unit, _ = m.groups()

    # приводим число к float
    num_str = (
        raw_num.replace(" ", "")
        .replace("\u00A0", "")
        .replace(",", ".")
    )
    try:
        value = float(num_str)
    except ValueError:
        return None

    multiplier = 1.0
    if unit:
        unit_low = unit.lower()
        if unit_low.startswith("млн"):
            multiplier = 1_000_000.0
        elif unit_low.startswith("тыс"):
            multiplier = 1_000.0
        elif unit_low.startswith("млрд"):
            multiplier = 1_000_000_000.0
        elif unit_low.startswith("трлн"):
            multiplier = 1_000_000_000_000.0

    return value * multiplier

def format_volume_rub(value: float | None) -> str | None:
    """
    Превращает число рублей в строку:
    2_000_000   -> '2 млн. ₽'
    3_000       -> '3 тыс. ₽'
    3_400_000_000 -> '3.4 млрд. ₽'
    """
    if value is None:
        return None

    abs_val = abs(value)

    if abs_val >= 1_000_000_000_000:
        return f"{value/1_000_000_000_000:.3g} трлн. ₽"
    if abs_val >= 1_000_000_000:
        return f"{value/1_000_000_000:.3g} млрд. ₽"
    if abs_val >= 1_000_000:
        return f"{value/1_000_000:.3g} млн. ₽"
    if abs_val >= 1_000:
        return f"{value/1_000:.3g} тыс. ₽"

    # меньше тысячи — просто число + ₽
    return f"{value:,.0f} ₽".replace(",", " ")


def extract_news_text(html: str) -> str:
    """
    Достаёт текст только из div.article__text.
    Убирает меню, рекламу, фильтры и весь лишний контент.
    """
    soup = BeautifulSoup(html, "html.parser")

    # На smartlab.news текст новости находится тут:
    container = soup.find("div", class_="article__text")
    if not container:
        return ""

    # Собираем текст только из этого контейнера
    text = container.get_text(separator="\n", strip=True)

    # Удаляем лишние пустые строки
    lines = [l.strip() for l in text.splitlines()]
    lines = [l for l in lines if l]

    return "\n".join(lines)

