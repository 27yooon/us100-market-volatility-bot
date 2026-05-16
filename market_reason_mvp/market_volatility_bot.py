#!/usr/bin/env python3
"""
Step 1 MVP for the market-reason project.

Detects large 5-minute moves in Nasdaq-100 index data and sends a Telegram alert.
This script does not explain the reason yet; it only confirms that the event
triggering pipeline works.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


PROJECT_DIR = Path(__file__).resolve().parent
ROOT = PROJECT_DIR.parent
AUTOTRADE_ENV = ROOT / "autotrade_mvp" / ".env"
STATE_FILE = PROJECT_DIR / "state.json"
LOG_DIR = PROJECT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

KST = ZoneInfo("Asia/Seoul")
YAHOO_CHART_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
DEFAULT_SYMBOL = "^NDX"
DEFAULT_THRESHOLD_PCT = 0.40
DEFAULT_THRESHOLD_POINTS = 0.0
DEFAULT_POLL_SECONDS = 60
DEFAULT_HEARTBEAT_MINUTES = 10
CONTEXT_SYMBOLS: dict[str, str] = {
    "US10Y": "^TNX",
    "DXY": "DX-Y.NYB",
    "WTI": "CL=F",
    "VIX": "^VIX",
    "SOX": "^SOX",
}


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


def send_telegram_message(text: str) -> tuple[bool, str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return False, "telegram_not_configured"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    body = json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=15) as response:
            data = response.read().decode("utf-8", "replace")
        return True, data
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        return False, f"http_{exc.code}:{detail}"
    except URLError as exc:
        return False, f"url_error:{exc.reason}"
    except TimeoutError:
        return False, "timeout"


def fetch_recent_bars(symbol: str) -> dict[str, Any]:
    params = {
        "interval": "5m",
        "range": "2d",
        "includePrePost": "true",
    }
    url = f"{YAHOO_CHART_BASE}/{symbol}?{urlencode(params)}"
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        },
        method="GET",
    )
    with urlopen(request, timeout=20) as response:
        payload = response.read().decode("utf-8", "replace")
    return json.loads(payload)


@dataclass
class MoveSignal:
    bar_time: int
    close: float
    prev_close: float
    move_pct: float
    move_points: float
    direction: str


@dataclass
class ContextMove:
    label: str
    symbol: str
    close: float
    prev_close: float
    move_pct: float
    move_points: float
    direction: str


def extract_move_signal(data: dict[str, Any], threshold_pct: float, threshold_points: float) -> MoveSignal | None:
    result = data["chart"]["result"][0]
    timestamps = result.get("timestamp") or []
    quote = result["indicators"]["quote"][0]
    closes = quote.get("close") or []

    cleaned: list[tuple[int, float]] = []
    for ts, close in zip(timestamps, closes):
        if ts is None or close is None:
            continue
        cleaned.append((int(ts), float(close)))

    if len(cleaned) < 2:
        return None

    prev_ts, prev_close = cleaned[-2]
    bar_ts, close = cleaned[-1]
    if prev_close == 0:
        return None

    move_points = close - prev_close
    move_pct = ((close - prev_close) / prev_close) * 100.0
    pct_ok = abs(move_pct) >= threshold_pct if threshold_pct > 0 else False
    points_ok = abs(move_points) >= threshold_points if threshold_points > 0 else False
    if not pct_ok and not points_ok:
        return None

    direction = "UP" if move_pct > 0 else "DOWN"
    return MoveSignal(
        bar_time=bar_ts,
        close=close,
        prev_close=prev_close,
        move_pct=move_pct,
        move_points=move_points,
        direction=direction,
    )


def extract_latest_move(label: str, symbol: str, data: dict[str, Any]) -> ContextMove | None:
    result = data["chart"]["result"][0]
    timestamps = result.get("timestamp") or []
    quote = result["indicators"]["quote"][0]
    closes = quote.get("close") or []

    cleaned: list[tuple[int, float]] = []
    for ts, close in zip(timestamps, closes):
        if ts is None or close is None:
            continue
        cleaned.append((int(ts), float(close)))

    if len(cleaned) < 2:
        return None

    _, prev_close = cleaned[-2]
    _, close = cleaned[-1]
    if prev_close == 0:
        return None

    move_points = close - prev_close
    move_pct = ((close - prev_close) / prev_close) * 100.0
    direction = "UP" if move_pct > 0 else "DOWN" if move_pct < 0 else "FLAT"
    return ContextMove(
        label=label,
        symbol=symbol,
        close=close,
        prev_close=prev_close,
        move_pct=move_pct,
        move_points=move_points,
        direction=direction,
    )


def fetch_context_snapshot() -> list[ContextMove]:
    moves: list[ContextMove] = []
    for label, symbol in CONTEXT_SYMBOLS.items():
        try:
            data = fetch_recent_bars(symbol)
            move = extract_latest_move(label, symbol, data)
            if move is not None:
                moves.append(move)
        except Exception:
            continue
    return moves


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(state: dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def kst_time_string(unix_ts: int) -> str:
    dt = datetime.fromtimestamp(unix_ts, tz=timezone.utc).astimezone(KST)
    return dt.strftime("%Y-%m-%d %H:%M:%S KST")


def format_context_line(move: ContextMove) -> str:
    arrow = "↑" if move.direction == "UP" else "↓" if move.direction == "DOWN" else "="
    return f"{move.label}: {arrow} {move.move_pct:+.2f}% ({move.close:.2f})"


def format_alert_message(
    symbol: str,
    signal: MoveSignal,
    threshold_pct: float,
    threshold_points: float,
    context_moves: list[ContextMove],
) -> str:
    bar_time = kst_time_string(signal.bar_time)
    arrow = "급등" if signal.direction == "UP" else "급락"
    if threshold_points > 0:
        trigger_line = f"기준: 5분 {threshold_points:.1f}포인트 이상"
    else:
        trigger_line = f"기준: 5분 {threshold_pct:.2f}% 이상"
    lines = [
        f"NASDAQ 급변 감지 ({arrow})",
        f"기준 종목: {symbol}",
        trigger_line,
        f"현재 방향: {signal.direction}",
        f"변동 포인트: {signal.move_points:+.2f}",
        f"변동률: {signal.move_pct:+.2f}%",
        f"직전 종가: {signal.prev_close:.2f}",
        f"현재 종가: {signal.close:.2f}",
        f"기준 시각: {bar_time}",
    ]
    if context_moves:
        lines.append("")
        lines.append("시장 체크:")
        lines.extend(format_context_line(move) for move in context_moves)
    return "\n".join(lines)


def append_log(record: dict[str, Any]) -> None:
    path = LOG_DIR / "market_reason_events.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def run_once(symbol: str, threshold_pct: float, threshold_points: float, quiet_no_move: bool = False) -> int:
    data = fetch_recent_bars(symbol)
    signal = extract_move_signal(data, threshold_pct=threshold_pct, threshold_points=threshold_points)
    if signal is None:
        if not quiet_no_move:
            print(f"No large 5-minute move detected for {symbol}.")
        return 0

    state = load_state()
    dedupe_key = f"{symbol}:{signal.bar_time}:{signal.direction}"
    if state.get("last_alert_key") == dedupe_key:
        if not quiet_no_move:
            print("Duplicate signal already sent for this bar.")
        return 0

    context_moves = fetch_context_snapshot()
    text = format_alert_message(symbol, signal, threshold_pct, threshold_points, context_moves)
    ok, detail = send_telegram_message(text)
    record = {
        "sent_at": datetime.now(tz=timezone.utc).isoformat(),
        "symbol": symbol,
        "bar_time": signal.bar_time,
        "direction": signal.direction,
        "move_points": signal.move_points,
        "move_pct": signal.move_pct,
        "close": signal.close,
        "prev_close": signal.prev_close,
        "threshold_pct": threshold_pct,
        "threshold_points": threshold_points,
        "context": [
            {
                "label": move.label,
                "symbol": move.symbol,
                "close": move.close,
                "move_pct": move.move_pct,
                "move_points": move.move_points,
                "direction": move.direction,
            }
            for move in context_moves
        ],
        "telegram_ok": ok,
        "telegram_detail": detail if ok else detail[:500],
    }
    append_log(record)

    if not ok:
        print(f"Telegram send failed: {detail}")
        return 1

    state["last_alert_key"] = dedupe_key
    save_state(state)
    print("Alert sent.")
    return 0


def run_loop(
    symbol: str,
    threshold_pct: float,
    threshold_points: float,
    poll_seconds: int,
    heartbeat_minutes: int,
) -> int:
    threshold_label = f"{threshold_points:.1f}pt" if threshold_points > 0 else f"{threshold_pct:.2f}%"
    print(
        f"Starting loop. symbol={symbol} threshold={threshold_label} "
        f"poll={poll_seconds}s heartbeat={heartbeat_minutes}m"
    )
    checks_since_heartbeat = 0
    heartbeat_every_checks = max(1, int((heartbeat_minutes * 60) / poll_seconds))
    while True:
        try:
            run_once(symbol, threshold_pct, threshold_points, quiet_no_move=True)
            checks_since_heartbeat += 1
            if checks_since_heartbeat >= heartbeat_every_checks:
                now_kst = datetime.now(tz=timezone.utc).astimezone(KST).strftime("%Y-%m-%d %H:%M:%S KST")
                print(f"Waiting... no large move yet for {symbol} ({now_kst})")
                checks_since_heartbeat = 0
        except Exception as exc:  # noqa: BLE001
            append_log(
                {
                    "sent_at": datetime.now(tz=timezone.utc).isoformat(),
                    "type": "error",
                    "message": str(exc),
                }
            )
            print(f"Loop error: {exc}", file=sys.stderr)
        time.sleep(poll_seconds)


def parse_args(argv: list[str]) -> tuple[bool, str, float, float, int, int]:
    once = "--once" in argv
    symbol = DEFAULT_SYMBOL
    threshold_pct = DEFAULT_THRESHOLD_PCT
    threshold_points = DEFAULT_THRESHOLD_POINTS
    poll_seconds = DEFAULT_POLL_SECONDS
    heartbeat_minutes = DEFAULT_HEARTBEAT_MINUTES

    for arg in argv:
        if arg.startswith("--symbol="):
            symbol = arg.split("=", 1)[1]
        if arg.startswith("--threshold="):
            threshold_pct = float(arg.split("=", 1)[1])
        elif arg.startswith("--threshold-points="):
            threshold_points = float(arg.split("=", 1)[1])
        elif arg.startswith("--poll="):
            poll_seconds = int(arg.split("=", 1)[1])
        elif arg.startswith("--heartbeat-minutes="):
            heartbeat_minutes = int(arg.split("=", 1)[1])
    if threshold_points > 0:
        threshold_pct = 0.0
    return once, symbol, threshold_pct, threshold_points, poll_seconds, heartbeat_minutes


def main(argv: list[str]) -> int:
    load_env_file(AUTOTRADE_ENV)
    once, symbol, threshold_pct, threshold_points, poll_seconds, heartbeat_minutes = parse_args(argv)

    if not os.environ.get("TELEGRAM_BOT_TOKEN") or not os.environ.get("TELEGRAM_CHAT_ID"):
        print("Telegram env is missing. Check autotrade_mvp/.env first.", file=sys.stderr)
        return 1

    if once:
        return run_once(symbol, threshold_pct, threshold_points)
    return run_loop(symbol, threshold_pct, threshold_points, poll_seconds, heartbeat_minutes)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
