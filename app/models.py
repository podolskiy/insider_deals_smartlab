from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import date
from pydantic import BaseModel

from app.parsers import format_volume_rub


class InsiderDealType(str, Enum):
    BUYBACK = "BUYBACK"
    OTHER = "OTHER"


@dataclass
class InsiderDeal:
    issuer_name: str
    issuer_ticker: str
    deal_type: InsiderDealType
    shares_count: Optional[int]
    deal_date: Optional[date]
    source_url: str
    raw_text: str
    volume_rub: Optional[float] = None 


class InsiderDealDTO(BaseModel):
    issuer_name: str
    issuer_ticker: str
    deal_type: InsiderDealType
    shares_count: Optional[int]
    deal_date: Optional[date]
    source_url: str
    volume_formatted: Optional[str] = None
    volume_rub: Optional[float] = None

    @classmethod
    def from_db(cls, row) -> "InsiderDealDTO":
        return cls(
            issuer_name=row.issuer_name,
            issuer_ticker=row.issuer_ticker,
            deal_type=InsiderDealType(row.deal_type),
            shares_count=row.shares_count,
            deal_date=row.deal_date,
            source_url=row.source_url,
            volume_rub=row.volume_rub,
            volume_formatted=format_volume_rub(row.volume_rub),
        )
