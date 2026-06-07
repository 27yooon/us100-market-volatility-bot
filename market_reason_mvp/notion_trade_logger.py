#!/usr/bin/env python3
"""
Optional Notion database logger for 쭈꾸미 paper-trading events.

Secrets must be provided through environment variables only.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


NOTION_API_URL = "https://api.notion.com/v1/pages"
NOTION_VERSION = "2022-06-28"


def enabled() -> bool:
    return bool(os.environ.get("NOTION_API_TOKEN") and os.environ.get("NOTION_DATABASE_ID"))


def _plain_text(value: Any, limit: int = 1800) -> list[dict[str, Any]]:
    text = "" if value is None else str(value)
    if len(text) > limit:
        text = text[: limit - 3] + "..."
    return [{"type": "text", "text": {"content": text}}]


def _title(value: Any) -> list[dict[str, Any]]:
    return _plain_text(value, limit=200)


def _number(value: Any) -> dict[str, Any]:
    try:
        if value is None or value == "":
            return {"number": None}
        return {"number": float(value)}
    except (TypeError, ValueError):
        return {"number": None}


def _select(value: Any) -> dict[str, Any]:
    if value is None or value == "":
        return {"select": None}
    return {"select": {"name": str(value)}}


def _checkbox(value: Any) -> dict[str, Any]:
    return {"checkbox": bool(value)}


def _date(value: Any) -> dict[str, Any]:
    if not value:
        return {"date": None}
    text = str(value).replace(" KST", "+09:00")
    # Notion accepts ISO-ish values. Keep date-only values date-only.
    if len(text) == 10:
        return {"date": {"start": text}}
    if " " in text and "T" not in text:
        text = text.replace(" ", "T", 1)
    return {"date": {"start": text}}


def _join_list(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    return "" if value is None else str(value)


def _event_title(record: dict[str, Any]) -> str:
    event = record.get("event", "-")
    strategy = record.get("strategy", "render")
    side = record.get("side", "-")
    result = record.get("result") or record.get("candidate_result") or ""
    ts = record.get("opened_at_text") or record.get("closed_at_text") or record.get("logged_at") or ""
    setup = record.get("setup_type") or record.get("mode") or "상태 확인"
    parts = [str(ts), str(event), str(strategy)]
    if side != "-":
        parts.append(str(side))
    parts.append(str(setup))
    if result:
        parts.append(str(result))
    return " ".join(part for part in parts if part).strip()


def build_properties(record: dict[str, Any]) -> dict[str, Any]:
    summaries = record.get("summaries") or {}
    z_summary = summaries.get("zukkumi_original") or summaries.get("zukkumi_rules") or {}
    p_summary = summaries.get("indicator_basic") or summaries.get("public_indicator_rules") or {}
    strategy = record.get("strategy") or "render"
    event = record.get("event")
    opened_at = record.get("opened_at_text")
    closed_at = record.get("closed_at_text")
    date_source = closed_at or opened_at or record.get("logged_at")
    date_text = str(date_source)[:10] if date_source else ""
    pnl = record.get("pnl_points")
    if event == "HEARTBEAT" and strategy == "render":
        pnl = z_summary.get("pnl_points")

    properties: dict[str, Any] = {
        "Name": {"title": _title(_event_title(record))},
        "Date": _date(date_text),
        "Logged At": _date(record.get("logged_at")),
        "Opened At": _date(opened_at),
        "Closed At": _date(closed_at),
        "Strategy": _select(strategy),
        "Event": _select(event),
        "Symbol": _select(record.get("symbol")),
        "Side": _select(record.get("side") or "-"),
        "Setup": {"rich_text": _plain_text(record.get("setup_type") or record.get("mode") or "상태 확인")},
        "Level": _number(record.get("level")),
        "Entry": _number(record.get("entry")),
        "Stop": _number(record.get("stop")),
        "Target": _number(record.get("target")),
        "Exit": _number(record.get("exit_price")),
        "Result": _select(record.get("result") or "NONE"),
        "PnL": _number(pnl),
        "Open Position": _checkbox(bool(record.get("open_trade"))),
        "Reasons": {"rich_text": _plain_text(_join_list(record.get("reasons")))},
        "Cautions": {"rich_text": _plain_text(_join_list(record.get("cautions")))},
        "Close Reason": {"rich_text": _plain_text(record.get("close_reason"))},
        "Signal Key": {"rich_text": _plain_text(record.get("signal_key"))},
        "Candidate Status": _select(record.get("candidate_status")),
        "Candidate Result": _select(record.get("candidate_result")),
        "Filter Reason": {"rich_text": _plain_text(record.get("filter_reason"))},
        "Review Summary": {"rich_text": _plain_text(record.get("review_summary"))},
        "Observation Type": _select(record.get("observation_type")),
    }
    if event == "HEARTBEAT":
        properties.update(
            {
                "Z Trades": _number(z_summary.get("trades")),
                "Z Wins": _number(z_summary.get("wins")),
                "Z Losses": _number(z_summary.get("losses")),
                "Z PnL": _number(z_summary.get("pnl_points")),
                "Z Candidate Open": _number(z_summary.get("candidate_open")),
                "Z Missed Entries": _number(z_summary.get("missed_entries")),
                "Z Filtered OK": _number(z_summary.get("filtered_ok")),
                "Z Ambiguous": _number(z_summary.get("ambiguous")),
                "Z Observations": _number(z_summary.get("observations")),
                "P Trades": _number(p_summary.get("trades")),
                "P Wins": _number(p_summary.get("wins")),
                "P Losses": _number(p_summary.get("losses")),
                "P PnL": _number(p_summary.get("pnl_points")),
                "P Candidate Open": _number(p_summary.get("candidate_open")),
                "P Missed Entries": _number(p_summary.get("missed_entries")),
                "P Filtered OK": _number(p_summary.get("filtered_ok")),
                "P Ambiguous": _number(p_summary.get("ambiguous")),
                "P Observations": _number(p_summary.get("observations")),
            }
        )
    return properties


def send(record: dict[str, Any]) -> bool:
    token = os.environ.get("NOTION_API_TOKEN", "").strip()
    database_id = os.environ.get("NOTION_DATABASE_ID", "").strip()
    if not token or not database_id:
        return False

    payload = {
        "parent": {"database_id": database_id},
        "properties": build_properties(record),
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        NOTION_API_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        },
    )
    try:
        with urlopen(request, timeout=10) as response:
            return 200 <= response.status < 300
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        print(f"notion_log_error={type(exc).__name__}: {exc}", flush=True)
        return False
