#!/usr/bin/env python3
"""
Run two paper-trading strategies continuously for Render Background Worker.

No Telegram messages are sent and no real orders are placed.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import market_signal_bot as bot


LOG_DIR = bot.PROJECT_DIR / "logs"
STATE_PATH = LOG_DIR / "render_dual_paper_state.json"
JSONL_PATH = LOG_DIR / "render_dual_paper_events.jsonl"


@dataclass(frozen=True)
class PaperSignal:
    side: str
    setup_type: str
    level: int
    entry: float
    stop: float
    target: float
    bar_time: int
    reasons: list[str]
    cautions: list[str]


def now_text() -> str:
    return datetime.now(bot.KST).strftime("%Y-%m-%d %H:%M:%S KST")


def text_time(unix_ts: int) -> str:
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc).astimezone(bot.KST).strftime("%Y-%m-%d %H:%M:%S KST")


def append_event(record: dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    record = {"logged_at": now_text(), **record}
    with JSONL_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps(record, ensure_ascii=False), flush=True)


def initial_strategy_state() -> dict[str, Any]:
    return {"open_trade": None, "closed_trades": [], "seen_signal_keys": []}


def load_state(reset: bool) -> dict[str, Any]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if reset:
        for path in (STATE_PATH, JSONL_PATH):
            if path.exists():
                path.unlink()
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {
        "session_started_at": now_text(),
        "mode": "render_dual_paper",
        "strategies": {
            "zukkumi_rules": initial_strategy_state(),
            "public_indicator_rules": initial_strategy_state(),
        },
    }


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def ema(values: list[float], n: int) -> list[float]:
    if not values:
        return []
    alpha = 2 / (n + 1)
    out = [values[0]]
    for value in values[1:]:
        out.append((value * alpha) + (out[-1] * (1 - alpha)))
    return out


def rsi(values: list[float], n: int = 14) -> float | None:
    if len(values) <= n:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for prev, curr in zip(values[-n - 1 : -1], values[-n:]):
        change = curr - prev
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain = sum(gains) / n
    avg_loss = sum(losses) / n
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def atr(bars: list[bot.Bar], n: int = 14) -> float | None:
    if len(bars) <= n:
        return None
    trs: list[float] = []
    recent = bars[-n:]
    prev_close = bars[-n - 1].close
    for bar in recent:
        trs.append(max(bar.high - bar.low, abs(bar.high - prev_close), abs(bar.low - prev_close)))
        prev_close = bar.close
    return sum(trs) / len(trs)


def bollinger(values: list[float], n: int = 20, k: float = 2.0) -> tuple[float, float, float] | None:
    if len(values) < n:
        return None
    recent = values[-n:]
    mid = sum(recent) / n
    variance = sum((value - mid) ** 2 for value in recent) / n
    std = math.sqrt(variance)
    return mid, mid + k * std, mid - k * std


def signal_key(strategy: str, symbol: str, signal: PaperSignal) -> str:
    return f"{strategy}:{symbol}:{signal.bar_time}:{signal.side}:{signal.setup_type}:{round(signal.entry, 1)}"


def zukkumi_signal(
    symbol: str,
    bars: list[bot.Bar],
    pivots: bot.PivotLevels | None,
    context: list[bot.MarketMove],
    min_level: int,
    min_rr: float,
) -> PaperSignal | None:
    candidate = bot.analyze_signal(bars, pivots, context, min_rr)
    if candidate is None or candidate.level < min_level:
        return None
    if "라운딩" not in candidate.setup_type and "P라인" not in candidate.setup_type:
        return None
    target = candidate.entry + 50 if candidate.side == "LONG" else candidate.entry - 50
    return PaperSignal(
        side=candidate.side,
        setup_type=candidate.setup_type,
        level=candidate.level,
        entry=candidate.entry,
        stop=candidate.stop,
        target=target,
        bar_time=candidate.bar_time,
        reasons=candidate.reasons,
        cautions=candidate.cautions,
    )


def public_indicator_signal(bars: list[bot.Bar], min_level: int) -> PaperSignal | None:
    if len(bars) < 80:
        return None
    closes = [bar.close for bar in bars]
    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    current_rsi = rsi(closes, 14)
    current_atr = atr(bars, 14)
    bands = bollinger(closes, 20)
    if current_rsi is None or current_atr is None or bands is None:
        return None

    last = bars[-1]
    prev = bars[-2]
    _, upper, lower = bands
    recent = bars[-8:]
    recent_low = min(bar.low for bar in recent)
    recent_high = max(bar.high for bar in recent)
    touched_lower = any(bar.low <= lower for bar in recent)
    touched_upper = any(bar.high >= upper for bar in recent)
    recovered_long = prev.close <= ema20[-2] and last.close > ema20[-1]
    recovered_short = prev.close >= ema20[-2] and last.close < ema20[-1]
    up_bias = ema20[-1] >= ema50[-1]
    down_bias = ema20[-1] <= ema50[-1]

    if touched_lower and recovered_long and current_rsi < 48 and up_bias:
        stop = min(recent_low - (current_atr * 0.2), last.close - max(20.0, current_atr * 1.2))
        risk = last.close - stop
        target = last.close + 50
        rr = 50 / risk if risk > 0 else 0
        if rr >= 1.2 and min_level <= 3:
            return PaperSignal(
                side="LONG",
                setup_type="공개기술지표 반등 롱",
                level=3,
                entry=last.close,
                stop=stop,
                target=target,
                bar_time=last.ts,
                reasons=[
                    "Bollinger 하단 터치 후 EMA20 회복",
                    f"RSI14 {current_rsi:.1f}, EMA20>=EMA50",
                ],
                cautions=["TradingAgents-CN식 기술지표 참고 룰. 실전 신호 아님"],
            )

    if touched_upper and recovered_short and current_rsi > 52 and down_bias:
        stop = max(recent_high + (current_atr * 0.2), last.close + max(20.0, current_atr * 1.2))
        risk = stop - last.close
        target = last.close - 50
        rr = 50 / risk if risk > 0 else 0
        if rr >= 1.2 and min_level <= 3:
            return PaperSignal(
                side="SHORT",
                setup_type="공개기술지표 반락 숏",
                level=3,
                entry=last.close,
                stop=stop,
                target=target,
                bar_time=last.ts,
                reasons=[
                    "Bollinger 상단 터치 후 EMA20 이탈",
                    f"RSI14 {current_rsi:.1f}, EMA20<=EMA50",
                ],
                cautions=["TradingAgents-CN식 기술지표 참고 룰. 실전 신호 아님"],
            )
    return None


def update_open_trade(strategy: str, state: dict[str, Any], bars: list[bot.Bar]) -> None:
    trade = state.get("open_trade")
    if not trade:
        return
    future = [bar for bar in bars if bar.ts > trade["opened_at"]]
    for bar in future:
        if trade["side"] == "LONG":
            if bar.high >= trade["target"]:
                close_trade(strategy, state, trade, "WIN", trade["target"], bar.ts, "+50pt target hit")
                return
            if bar.close < trade["stop"]:
                close_trade(strategy, state, trade, "LOSS", bar.close, bar.ts, "5m close below stop")
                return
        else:
            if bar.low <= trade["target"]:
                close_trade(strategy, state, trade, "WIN", trade["target"], bar.ts, "+50pt target hit")
                return
            if bar.close > trade["stop"]:
                close_trade(strategy, state, trade, "LOSS", bar.close, bar.ts, "5m close above stop")
                return


def open_trade(strategy: str, state: dict[str, Any], symbol: str, signal: PaperSignal) -> None:
    trade = {
        "symbol": symbol,
        **asdict(signal),
        "opened_at": signal.bar_time,
        "opened_at_text": text_time(signal.bar_time),
        "signal_key": signal_key(strategy, symbol, signal),
    }
    state["open_trade"] = trade
    state["seen_signal_keys"] = [*state.get("seen_signal_keys", []), trade["signal_key"]][-300:]
    append_event({"strategy": strategy, "event": "OPEN", **trade})


def close_trade(
    strategy: str,
    state: dict[str, Any],
    trade: dict[str, Any],
    result: str,
    exit_price: float,
    closed_at: int,
    reason: str,
) -> None:
    pnl = exit_price - trade["entry"] if trade["side"] == "LONG" else trade["entry"] - exit_price
    closed = {
        **trade,
        "result": result,
        "exit_price": exit_price,
        "pnl_points": pnl,
        "closed_at": closed_at,
        "closed_at_text": text_time(closed_at),
        "close_reason": reason,
    }
    state["closed_trades"] = [*state.get("closed_trades", []), closed]
    state["open_trade"] = None
    append_event({"strategy": strategy, "event": "CLOSE", **closed})


def summary(strategy_state: dict[str, Any]) -> dict[str, Any]:
    trades = strategy_state.get("closed_trades", [])
    wins = sum(1 for trade in trades if trade.get("result") == "WIN")
    losses = sum(1 for trade in trades if trade.get("result") == "LOSS")
    pnl = sum(float(trade.get("pnl_points", 0.0)) for trade in trades)
    return {
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "pnl_points": round(pnl, 2),
        "open": bool(strategy_state.get("open_trade")),
    }


def run_tick(state: dict[str, Any], symbol: str, interval: str, range_name: str, min_rr: float) -> None:
    bars = bot.parse_bars(bot.fetch_chart(symbol, interval, range_name))
    pivots = bot.compute_pivots(symbol)
    try:
        context = bot.fetch_context_snapshot()
    except Exception:
        context = []

    strategies = state["strategies"]
    for name, strategy_state in strategies.items():
        update_open_trade(name, strategy_state, bars)
        if strategy_state.get("open_trade"):
            continue
        if name == "zukkumi_rules":
            signal = zukkumi_signal(symbol, bars, pivots, context, min_level=2, min_rr=min_rr)
        else:
            signal = public_indicator_signal(bars, min_level=3)
        if signal is None:
            continue
        key = signal_key(name, symbol, signal)
        if key in strategy_state.get("seen_signal_keys", []):
            continue
        open_trade(name, strategy_state, symbol, signal)

    append_event(
        {
            "event": "HEARTBEAT",
            "symbol": symbol,
            "price": bars[-1].close if bars else None,
            "summaries": {name: summary(strategy_state) for name, strategy_state in strategies.items()},
        }
    )
    save_state(state)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render worker for two paper strategies.")
    parser.add_argument("--symbol", default=bot.DEFAULT_SYMBOL)
    parser.add_argument("--interval", default=bot.DEFAULT_INTERVAL)
    parser.add_argument("--range", default=bot.DEFAULT_RANGE, dest="range_name")
    parser.add_argument("--poll", type=int, default=300)
    parser.add_argument("--min-rr", type=float, default=bot.DEFAULT_MIN_RR)
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    state = load_state(args.reset)
    append_event(
        {
            "event": "START",
            "mode": "render_dual_paper",
            "symbol": args.symbol,
            "poll": args.poll,
            "telegram": "disabled",
        }
    )
    while True:
        try:
            run_tick(state, args.symbol, args.interval, args.range_name, args.min_rr)
        except Exception as exc:  # noqa: BLE001
            append_event({"event": "ERROR", "message": str(exc)})
        if args.once:
            break
        time.sleep(max(30, args.poll))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
