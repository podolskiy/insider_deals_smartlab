from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Date, DateTime, Text, Float


class Base(DeclarativeBase):
    pass


class DealDB(Base):
    __tablename__ = "insider_deals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    issuer_name: Mapped[str] = mapped_column(String)
    issuer_ticker: Mapped[str] = mapped_column(String, default="")
    deal_type: Mapped[str] = mapped_column(String)  # BUYBACK / OTHER
    shares_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    deal_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    volume_rub: Mapped[Optional[float]] = mapped_column(Float, nullable=True, )
    source_url: Mapped[str] = mapped_column(String, unique=True)
    raw_text: Mapped[str] = mapped_column(Text)


class ScrapedArticle(Base):
    __tablename__ = "scraped_articles"

    url: Mapped[str] = mapped_column(String, primary_key=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ScraperError(Base):
    __tablename__ = "scraper_errors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String)
    error: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


DB_URL = "sqlite+aiosqlite:///./insiders.db"

engine = create_async_engine(DB_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
