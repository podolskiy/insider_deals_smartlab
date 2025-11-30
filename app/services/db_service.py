from __future__ import annotations

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import DealDB, ScrapedArticle, ScraperError
from app.models import InsiderDeal


async def is_article_loaded(session: AsyncSession, url: str) -> bool:
    res = await session.execute(select(ScrapedArticle).where(ScrapedArticle.url == url))
    return res.scalar_one_or_none() is not None


async def mark_article_loaded(session: AsyncSession, url: str) -> None:
    session.add(ScrapedArticle(url=url))
    await session.commit()


async def save_error(session: AsyncSession, url: str | None, source: str, error: str) -> None:
    session.add(ScraperError(url=url, source=source, error=error))
    await session.commit()


async def save_deal(session: AsyncSession, deal: InsiderDeal) -> None:
    res = await session.execute(select(DealDB).where(DealDB.source_url == deal.source_url))
    if res.scalar_one_or_none():
        return

    row = DealDB(
        issuer_name=deal.issuer_name,
        issuer_ticker=deal.issuer_ticker,
        deal_type=deal.deal_type.value,
        shares_count=deal.shares_count,
        deal_date=deal.deal_date,
        source_url=deal.source_url,
        raw_text=deal.raw_text,
    )
    row.source_url = deal.source_url

    session.add(row)
    await session.commit()


async def get_buybacks(session: AsyncSession):
    res = await session.execute(
        select(DealDB)
        .where(DealDB.deal_type == "BUYBACK")
        .where(DealDB.shares_count > 0)
        .order_by(DealDB.deal_date.desc().nullslast())
    )
    return res.scalars().all()


async def get_errors(session: AsyncSession):
    res = await session.execute(
        select(ScraperError).order_by(ScraperError.created_at.desc())
    )
    return res.scalars().all()

async def reset_all(session: AsyncSession) -> None:
    await session.execute(delete(DealDB))
    await session.execute(delete(ScrapedArticle))
    await session.execute(delete(ScraperError))
    await session.commit()
