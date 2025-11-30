from __future__ import annotations

import json
from fastapi.responses import JSONResponse
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from app.db import init_db, SessionLocal
from app.models import InsiderDealDTO
from app.services.db_service import get_buybacks, get_errors, reset_all
from app.sources.smartlab_news import SmartLabNewsSource
from app.logging_config import setup_logging
import logging

setup_logging()
log = logging.getLogger("main")


class PrettyJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            indent=2,
            default=str,
        ).encode("utf-8")

app = FastAPI(title="Insider deals smartlab",default_response_class=PrettyJSONResponse)

news_source = SmartLabNewsSource()
scheduler = AsyncIOScheduler()


async def hourly_update() -> None:
    async with SessionLocal() as session, httpx.AsyncClient() as client:
        await news_source.update(client, session)


@app.on_event("startup")
async def on_startup() -> None:
    log.info("Starting FastAPI service…")
    await init_db()
    await hourly_update()
    scheduler.add_job(hourly_update, "interval", hours=1)
    scheduler.start()
    log.info("Scheduler started")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    scheduler.shutdown(wait=False)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/update")
async def update_now() -> dict:
    await hourly_update()
    return {"status": "ok"}


@app.get("/buybacks", response_model=list[InsiderDealDTO])
async def buybacks():
    async with SessionLocal() as session:
        rows = await get_buybacks(session)
    return [InsiderDealDTO.from_db(r) for r in rows]


@app.get("/errors")
async def errors():
    async with SessionLocal() as session:
        rows = await get_errors(session)
    return [
        {
            "time": r.created_at,
            "source": r.source,
            "url": r.url,
            "error": r.error,
        }
        for r in rows
    ]

@app.post("/reset")
async def reset_db():
    async with SessionLocal() as session:
        await reset_all(session)
    return {"status": "reset"}