from __future__ import annotations

from typing import List
from urllib.parse import urljoin

import re
import httpx
from bs4 import BeautifulSoup

from app.data import infer_ticker
from app.models import InsiderDeal, InsiderDealType
from app.parsers import (
    extract_news_text,
    extract_visible_text,
    format_volume_rub,
    try_parse_shares_count,
    try_parse_first_russian_date,
    try_parse_volume_rub, 
)
from app.services.db_service import (
    is_article_loaded,
    mark_article_loaded,
    save_error,
    save_deal,
)
import logging
log = logging.getLogger("smartlab")

COMPANY_TICKER_RE = re.compile(
    r"/company/([A-Z0-9\-_.]+)", re.IGNORECASE
)

SMARTLAB_Q_RE = re.compile(
    r"/q/([A-Z0-9\-_.]+)/?", re.IGNORECASE
)


class SmartLabNewsSource:
    name = "smartlab.news"

    LIST_PAGES = [
        "https://smartlab.news/type/disclosure-insiders",
        # "https://smartlab.news/type/disclosure-insiders/page/2",
    ]

    async def update(self, client: httpx.AsyncClient, session) -> None:
        log.info("Starting update for smartlab.news")
        for list_url in self.LIST_PAGES:
            log.info(f"[LIST] Fetching list page: {list_url}")
            try:
                resp = await client.get(list_url, timeout=20.0)
                resp.raise_for_status()
                html = resp.text

                soup = BeautifulSoup(html, "html.parser")
                links = set()

                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if "/read/" not in href:
                        continue
                    full_url = href if href.startswith("http") else urljoin(
                        "https://smartlab.news", href
                    )
                    links.add(full_url)

                log.info(f"[LIST] Found {len(links)} article links")

                for url in links:
                    if await is_article_loaded(session, url):
                        log.info(f"[SKIP] Already loaded: {url}")
                        continue
                    await self._parse_article(client, session, url)

                log.info("Finished update for smartlab.news")
            except Exception as ex:
                await save_error(session, list_url, self.name, str(ex))

    async def _parse_article(
        self, client: httpx.AsyncClient, session, url: str
    ) -> None:
        log.info(f"[ARTICLE][START] {url}")
        try:
            resp = await client.get(url, timeout=20.0)
            resp.raise_for_status()
            html = resp.text

            text = extract_visible_text(html)
            issuer = self._extract_issuer_name(text)
            deal_type = self._detect_deal_type(text)
            shares = try_parse_shares_count(text)
            deal_date = try_parse_first_russian_date(text)
            volume_rub = try_parse_volume_rub(text)
            ticker = infer_ticker(issuer or "")
            raw_text = extract_news_text(html)

            if not ticker:
                ticker_from_link = self._extract_ticker_from_html(html)
                if ticker_from_link:
                    ticker = ticker_from_link

            deal = InsiderDeal(
                issuer_name=issuer or "",
                issuer_ticker=ticker,
                deal_type=deal_type,
                shares_count=shares,
                deal_date=deal_date,
                source_url=url,
                raw_text=raw_text,
                volume_rub=volume_rub,
            )
            await save_deal(session, deal)
            await mark_article_loaded(session, url)
            log.info(
            f"[ARTICLE][OK] {url} | issuer={issuer}, "
            f"type={deal_type}, shares={shares}, date={deal_date}, ticker={ticker}"
        )
        except Exception as ex:
            log.error(f"[ARTICLE][FETCH FAIL] {url} — {ex}", exc_info=True)
            await save_error(session, url, self.name, str(ex))

    @staticmethod
    def _extract_issuer_name(text: str) -> str | None:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            return None
        first = lines[0].strip("🤝📈📉 ").strip()
        # ожидаем формат "🤝Магнит- BUYBACK:  20.12.2024"
        for sep in ("- ", ":"):
            if sep in first:
                return first.split(sep, 1)[0].strip()
        return first

    @staticmethod
    def _detect_deal_type(text: str) -> InsiderDealType:
        upper = text.upper()
        if "BUYBACK" in upper or "БАЙБЕК" in upper:
            return InsiderDealType.BUYBACK
        return InsiderDealType.OTHER

    @staticmethod
    def _extract_ticker_from_html(html: str) -> str | None:
        """
        Пытаемся вытащить тикер из ссылок в статье:
        - https://smartlab.news/company/BELU
        - https://smart-lab.ru/q/SIBN/
        """
        soup = BeautifulSoup(html, "html.parser")

        for a in soup.find_all("a", href=True):
            href = a["href"]

            m = COMPANY_TICKER_RE.search(href)
            if m:
                return m.group(1).upper()

            m2 = SMARTLAB_Q_RE.search(href)
            if m2:
                return m2.group(1).upper()

        return None