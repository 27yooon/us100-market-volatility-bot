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


def _multi_select(value: Any, limit: int = 8) -> dict[str, Any]:
    if value is None or value == "":
        return {"multi_select": []}
    items = value if isinstance(value, list) else [value]
    names: list[str] = []
    for item in items:
        text = str(item).strip()
        if not text:
            continue
        if len(text) > 80:
            text = text[:77] + "..."
        if text not in names:
            names.append(text)
        if len(names) >= limit:
            break
    return {"multi_select": [{"name": name} for name in names]}


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


def _daily_report_summary(record: dict[str, Any]) -> str:
    if record.get("event") != "DAILY_REPORT":
        return ""
    totals = record.get("totals") or {}
    lines = [
        f"{record.get('report_title', '일일 보고')} / {record.get('report_date', '')}",
        f"총 진입 {int(totals.get('entries', 0))}회, 보유 {int(totals.get('open', 0))}건, 청산 {int(totals.get('closed', 0))}건",
        f"승패 {int(totals.get('wins', 0))}승 {int(totals.get('losses', 0))}패, 손익 {float(totals.get('pnl_points', 0.0)):+.2f}pt",
    ]
    for name, row in (record.get("strategies") or {}).items():
        if row.get("mode") == "watch_only":
            lines.append(f"{name}: 관찰 후보 {int(row.get('candidates', 0))}건")
        else:
            lines.append(
                f"{name}: 진입 {int(row.get('entries', 0))}회, "
                f"{int(row.get('wins', 0))}승 {int(row.get('losses', 0))}패, "
                f"{float(row.get('pnl_points', 0.0)):+.1f}pt"
            )
    return "\n".join(lines)


def _date_parts(date_text: str) -> tuple[str, str]:
    if len(date_text) < 7:
        return "", ""
    return date_text[:4], date_text[5:7]


def _event_title(record: dict[str, Any]) -> str:
    event = record.get("event", "-")
    strategy = record.get("strategy", "render")
    if event == "DAILY_REPORT":
        return f"{record.get('report_date', '')} {record.get('report_title', '일일 보고')}".strip()
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
    totals = record.get("totals") or {}
    pnl = record.get("pnl_points")
    if event == "HEARTBEAT" and strategy == "render":
        pnl = z_summary.get("pnl_points")
    if event == "DAILY_REPORT":
        pnl = totals.get("pnl_points")
    year_text, month_text = _date_parts(date_text)
    status = record.get("candidate_status") or record.get("result") or event or "기록"
    review_lines = [
        _daily_report_summary(record),
        record.get("review_summary"),
        _join_list(record.get("reasons")),
        _join_list(record.get("cautions")),
        record.get("close_reason"),
        record.get("filter_reason"),
        record.get("signal_key"),
    ]
    review_summary = "\n".join(str(line) for line in review_lines if line)

    properties: dict[str, Any] = {
        "매매명": {"title": _title(_event_title(record))},
        "날짜": _date(date_text),
        "연도": {"rich_text": _plain_text(year_text)},
        "월": {"rich_text": _plain_text(month_text)},
        "전략": _select(strategy),
        "매매법 구분": _select(event or record.get("mode") or "상태 확인"),
        "종목": {"rich_text": _plain_text(record.get("symbol"))},
        "포지션": _select(record.get("side") or "-"),
        "상태": _select(status),
        "진입가": _number(record.get("entry") or record.get("level")),
        "손절가": _number(record.get("stop")),
        "1차 익절가": _number(record.get("target")),
        "청산가": _number(record.get("exit_price")),
        "결과": _select(record.get("result") or record.get("candidate_result") or "NONE"),
        "손익(pt)": _number(pnl),
        "계약수": _number(record.get("contracts")),
        "R배수": _number(record.get("r_multiple")),
        "실수 여부": _checkbox(bool(record.get("mistake"))),
        "근거": _multi_select(record.get("reasons")),
        "복기": {"rich_text": _plain_text(review_summary)},
    }
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
