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
import notion_trade_logger


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
    rr: float | None = None
    invalidation: str | None = None
    observation_type: str | None = None


def now_text() -> str:
    return datetime.now(bot.KST).strftime("%Y-%m-%d %H:%M:%S KST")


def text_time(unix_ts: int) -> str:
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc).astimezone(bot.KST).strftime("%Y-%m-%d %H:%M:%S KST")


def session_label(unix_ts: int) -> str:
    local = datetime.fromtimestamp(unix_ts, tz=timezone.utc).astimezone(bot.KST)
    minutes = local.hour * 60 + local.minute
    if 17 * 60 <= minutes < 22 * 60 + 30:
        return "US_PREMARKET"
    if 22 * 60 + 30 <= minutes or minutes < 5 * 60:
        return "US_REGULAR"
    if 15 * 60 <= minutes < 17 * 60:
        return "EUROPE_TO_US_PRE"
    return "OFF_HOURS"


def append_event(record: dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    record = {"logged_at": now_text(), **record}
    with JSONL_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps(record, ensure_ascii=False), flush=True)
    if notion_trade_logger.enabled():
        notion_trade_logger.send(record)


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


def candidate_key(strategy: str, symbol: str, signal: PaperSignal) -> str:
    return f"candidate:{signal_key(strategy, symbol, signal)}"


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
        rr=candidate.rr,
        invalidation=candidate.invalidation,
    )


def zukkumi_observation_candidate(
    symbol: str,
    bars: list[bot.Bar],
    pivots: bot.PivotLevels | None,
    context: list[bot.MarketMove],
    observe_min_rr: float,
) -> PaperSignal | None:
    candidate = bot.analyze_signal(bars, pivots, context, observe_min_rr)
    if candidate is None:
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
        rr=candidate.rr,
        invalidation=candidate.invalidation,
    )


def paper_signal_from_candidate(candidate: bot.SignalCandidate, observation_type: str | None = None) -> PaperSignal:
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
        rr=candidate.rr,
        invalidation=candidate.invalidation,
        observation_type=observation_type,
    )


def rr_for_signal(side: str, entry: float, stop: float, target: float) -> float | None:
    risk = entry - stop if side == "LONG" else stop - entry
    reward = target - entry if side == "LONG" else entry - target
    if risk <= 0 or reward <= 0:
        return None
    return reward / risk


def build_observation_signal(
    side: str,
    setup_type: str,
    level: int,
    entry: float,
    stop: float,
    bar_time: int,
    reasons: list[str],
    cautions: list[str],
    observation_type: str,
) -> PaperSignal | None:
    target = entry + 50 if side == "LONG" else entry - 50
    rr = rr_for_signal(side, entry, stop, target)
    if rr is None:
        return None
    session = session_label(bar_time)
    enriched_reasons = [*reasons, f"세션 {session}"]
    invalidation = f"{stop:.2f} 아래 5분봉 마감" if side == "LONG" else f"{stop:.2f} 위 5분봉 마감"
    return PaperSignal(
        side=side,
        setup_type=setup_type,
        level=level,
        entry=entry,
        stop=stop,
        target=target,
        bar_time=bar_time,
        reasons=enriched_reasons,
        cautions=cautions,
        rr=rr,
        invalidation=invalidation,
        observation_type=observation_type,
    )


def broad_zukkumi_observation_candidates(
    bars: list[bot.Bar],
    pivots: bot.PivotLevels | None,
    context: list[bot.MarketMove],
    min_rr: float,
) -> list[PaperSignal]:
    if len(bars) < 80:
        return []

    closes = [bar.close for bar in bars]
    fast = ema(closes, 20)
    slow = ema(closes, 50)
    atr_value = atr(bars, 14)
    if atr_value is None or atr_value <= 0:
        return []

    last = bars[-1]
    recent = bars[-8:]
    base = bars[-6:]
    buffer = max(5.0, atr_value * 0.20)
    zone = max(15.0, atr_value * 0.75)
    out: list[PaperSignal] = []
    session = session_label(last.ts)
    premarket = session == "US_PREMARKET"

    def level_from_rr(rr: float | None, core_count: int) -> int:
        if rr is None:
            return 1
        if core_count >= 4 and rr >= min_rr:
            return 2
        if core_count >= 3:
            return 1
        return 1

    long_bias, short_bias, _ = bot.score_market_bias(context)
    fast_above = fast[-1] >= slow[-1]
    fast_below = fast[-1] <= slow[-1]
    recent_low = min(bar.low for bar in recent)
    recent_high = max(bar.high for bar in recent)

    if pivots is not None:
        pp = pivots.pp
        touched_p = any(bar.low <= pp + zone and bar.high >= pp - zone for bar in recent)
        if touched_p and last.close >= pp - zone:
            reasons = [f"P라인 관찰 구간({pp:.2f})", "P라인 근처 저점/회복 후보"]
            cautions: list[str] = []
            if recent_low >= pp - zone:
                reasons.append("P라인 근처 가격 방어")
            if last.close >= fast[-1] - atr_value * 0.20:
                reasons.append("EMA20 근처 회복 시도")
            else:
                cautions.append("아직 EMA20 아래")
            if fast_above:
                reasons.append("EMA20/50 상승 우위")
            if short_bias > long_bias + 1:
                cautions.append("시장 보조지표는 롱에 불리")
            stop = min(recent_low, pp) - buffer
            signal = build_observation_signal(
                "LONG",
                "P라인 관찰 롱",
                level_from_rr(rr_for_signal("LONG", last.close, stop, last.close + 50), len(reasons)),
                last.close,
                stop,
                last.ts,
                reasons,
                cautions,
                "OBSERVATION",
            )
            if signal is not None:
                out.append(signal)

        if touched_p and last.close <= pp + zone:
            reasons = [f"P라인 관찰 구간({pp:.2f})", "P라인 근처 반등/저항 후보"]
            cautions = []
            if recent_high <= pp + zone:
                reasons.append("P라인 근처 돌파 제한")
            if last.close <= fast[-1] + atr_value * 0.20:
                reasons.append("EMA20 아래 재하락 시도")
            else:
                cautions.append("아직 EMA20 위")
            if fast_below:
                reasons.append("EMA20/50 하락 우위")
            if long_bias > short_bias + 1:
                cautions.append("시장 보조지표는 숏에 불리")
            stop = max(recent_high, pp) + buffer
            signal = build_observation_signal(
                "SHORT",
                "P라인 관찰 숏",
                level_from_rr(rr_for_signal("SHORT", last.close, stop, last.close - 50), len(reasons)),
                last.close,
                stop,
                last.ts,
                reasons,
                cautions,
                "OBSERVATION",
            )
            if signal is not None:
                out.append(signal)

    base_high = max(bar.high for bar in base)
    base_low = min(bar.low for bar in base)
    base_range = base_high - base_low
    previous = bars[-18:-6]
    previous_range = (max(bar.high for bar in previous) - min(bar.low for bar in previous)) if previous else 0
    quiet_multiplier = 1.80 if premarket else 1.50
    previous_ratio = 0.70 if premarket else 0.55
    quiet_base = base_range <= max(atr_value * quiet_multiplier, previous_range * previous_ratio)
    if quiet_base:
        previous_high = max(bar.high for bar in previous)
        previous_low = min(bar.low for bar in previous)
        drop_into_base = previous_high - base_low
        rise_into_base = base_high - previous_low

        drop_threshold = atr_value * (0.70 if premarket else 1.00)
        rise_threshold = atr_value * (0.70 if premarket else 1.00)

        if drop_into_base >= drop_threshold and last.close >= base_low + base_range * 0.30:
            reasons = ["라운딩 관찰 바닥", "하락 후 봉 축소/횡보", "저점 재이탈 여부 관찰"]
            cautions = []
            if premarket:
                reasons.append("프리장 라인 미터치 라운딩 허용")
            if last.close >= fast[-1] - atr_value * 0.20:
                reasons.append("EMA20 회복 시도")
            else:
                cautions.append("EMA20 아래라 확인 필요")
            stop = base_low - buffer
            signal = build_observation_signal(
                "LONG",
                "라운딩 관찰 롱",
                level_from_rr(rr_for_signal("LONG", last.close, stop, last.close + 50), len(reasons)),
                last.close,
                stop,
                last.ts,
                reasons,
                cautions,
                "OBSERVATION",
            )
            if signal is not None:
                out.append(signal)

        if rise_into_base >= rise_threshold and last.close <= base_high - base_range * 0.30:
            reasons = ["라운딩 관찰 천장", "상승 후 봉 축소/횡보", "고점 재돌파 여부 관찰"]
            cautions = []
            if premarket:
                reasons.append("프리장 라인 미터치 라운딩 허용")
            if last.close <= fast[-1] + atr_value * 0.20:
                reasons.append("EMA20 이탈 시도")
            else:
                cautions.append("EMA20 위라 확인 필요")
            stop = base_high + buffer
            signal = build_observation_signal(
                "SHORT",
                "라운딩 관찰 숏",
                level_from_rr(rr_for_signal("SHORT", last.close, stop, last.close - 50), len(reasons)),
                last.close,
                stop,
                last.ts,
                reasons,
                cautions,
                "OBSERVATION",
            )
            if signal is not None:
                out.append(signal)

    deduped: dict[str, PaperSignal] = {}
    for signal in out:
        key = f"{signal.side}:{signal.setup_type}:{round(signal.entry / 10) * 10}"
        existing = deduped.get(key)
        if existing is None or (signal.rr or 0) > (existing.rr or 0):
            deduped[key] = signal
    return list(deduped.values())[:4]


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


def candidate_filter_reason(signal: PaperSignal, trade_min_level: int, trade_min_rr: float) -> str:
    reasons: list[str] = []
    if signal.observation_type:
        reasons.append(f"{signal.observation_type.lower()} only")
    if signal.level < trade_min_level:
        reasons.append(f"level {signal.level} < {trade_min_level}")
    if signal.rr is not None and signal.rr < trade_min_rr:
        reasons.append(f"rr {signal.rr:.2f} < {trade_min_rr:.2f}")
    if not reasons:
        reasons.append("strategy filter or duplicate/open trade")
    return ", ".join(reasons)


def open_candidate(
    strategy: str,
    state: dict[str, Any],
    symbol: str,
    signal: PaperSignal,
    status: str,
    filter_reason: str,
) -> None:
    key = candidate_key(strategy, symbol, signal)
    if key in state.get("seen_candidate_keys", []):
        return
    candidate = {
        "symbol": symbol,
        **asdict(signal),
        "candidate_status": status,
        "filter_reason": filter_reason,
        "observed_at": signal.bar_time,
        "observed_at_text": text_time(signal.bar_time),
        "signal_key": key,
        "review_summary": "진입 보류 후보. 후행으로 +50pt 또는 무효 기준 선행 여부를 확인한다.",
    }
    state["watch_candidates"] = [*state.get("watch_candidates", []), candidate][-200:]
    state["seen_candidate_keys"] = [*state.get("seen_candidate_keys", []), key][-500:]
    append_event({"strategy": strategy, "event": "CANDIDATE_OPEN", **candidate})


def update_watch_candidates(strategy: str, state: dict[str, Any], bars: list[bot.Bar]) -> None:
    candidates = state.get("watch_candidates", [])
    if not candidates:
        return

    updated: list[dict[str, Any]] = []
    for candidate in candidates:
        if candidate.get("candidate_result"):
            updated.append(candidate)
            continue

        future = [bar for bar in bars if bar.ts > candidate["observed_at"]]
        resolved: dict[str, Any] | None = None
        for bar in future:
            if candidate["side"] == "LONG":
                hit_target = bar.high >= candidate["target"]
                hit_stop = bar.close < candidate["stop"]
                if hit_target and hit_stop:
                    result = "AMBIGUOUS"
                    exit_price = bar.close
                    reason = "target and invalidation appeared in same 5m bar"
                elif hit_target:
                    result = "MISSED_ENTRY"
                    exit_price = candidate["target"]
                    reason = "+50pt target would have hit"
                elif hit_stop:
                    result = "FILTERED_OK"
                    exit_price = bar.close
                    reason = "invalidation would have hit first"
                else:
                    continue
            else:
                hit_target = bar.low <= candidate["target"]
                hit_stop = bar.close > candidate["stop"]
                if hit_target and hit_stop:
                    result = "AMBIGUOUS"
                    exit_price = bar.close
                    reason = "target and invalidation appeared in same 5m bar"
                elif hit_target:
                    result = "MISSED_ENTRY"
                    exit_price = candidate["target"]
                    reason = "+50pt target would have hit"
                elif hit_stop:
                    result = "FILTERED_OK"
                    exit_price = bar.close
                    reason = "invalidation would have hit first"
                else:
                    continue

            pnl = exit_price - candidate["entry"] if candidate["side"] == "LONG" else candidate["entry"] - exit_price
            resolved = {
                **candidate,
                "candidate_result": result,
                "exit_price": exit_price,
                "pnl_points": pnl,
                "closed_at": bar.ts,
                "closed_at_text": text_time(bar.ts),
                "close_reason": reason,
                "review_summary": (
                    "놓친 진입 후보" if result == "MISSED_ENTRY" else
                    "안 들어간 게 맞았던 후보" if result == "FILTERED_OK" else
                    "동일 5분봉 안에서 목표/무효가 함께 보여 수동 복기 필요"
                ),
            }
            append_event({"strategy": strategy, "event": "CANDIDATE_CLOSE", **resolved})
            break

        updated.append(resolved or candidate)

    state["watch_candidates"] = updated[-200:]


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
    candidates = strategy_state.get("watch_candidates", [])
    wins = sum(1 for trade in trades if trade.get("result") == "WIN")
    losses = sum(1 for trade in trades if trade.get("result") == "LOSS")
    pnl = sum(float(trade.get("pnl_points", 0.0)) for trade in trades)
    missed = sum(1 for candidate in candidates if candidate.get("candidate_result") == "MISSED_ENTRY")
    filtered_ok = sum(1 for candidate in candidates if candidate.get("candidate_result") == "FILTERED_OK")
    ambiguous = sum(1 for candidate in candidates if candidate.get("candidate_result") == "AMBIGUOUS")
    candidate_open = sum(1 for candidate in candidates if not candidate.get("candidate_result"))
    observation_count = sum(1 for candidate in candidates if candidate.get("observation_type") == "OBSERVATION")
    return {
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "pnl_points": round(pnl, 2),
        "open": bool(strategy_state.get("open_trade")),
        "candidate_open": candidate_open,
        "missed_entries": missed,
        "filtered_ok": filtered_ok,
        "ambiguous": ambiguous,
        "observations": observation_count,
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
        update_watch_candidates(name, strategy_state, bars)
        if strategy_state.get("open_trade"):
            continue
        if name == "zukkumi_rules":
            signal = zukkumi_signal(symbol, bars, pivots, context, min_level=2, min_rr=min_rr)
            observations = []
            strict_observation = zukkumi_observation_candidate(symbol, bars, pivots, context, observe_min_rr=0.50)
            if strict_observation is not None:
                observations.append(strict_observation)
            observations.extend(broad_zukkumi_observation_candidates(bars, pivots, context, min_rr=min_rr))
        else:
            signal = public_indicator_signal(bars, min_level=3)
            observations = [signal] if signal is not None else []
        if signal is None:
            for observation in observations:
                open_candidate(
                    name,
                    strategy_state,
                    symbol,
                    observation,
                    status="OBSERVATION_CANDIDATE" if observation.observation_type == "OBSERVATION" else "NO_TRADE_CANDIDATE",
                    filter_reason=candidate_filter_reason(observation, trade_min_level=2 if name == "zukkumi_rules" else 3, trade_min_rr=min_rr),
                )
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
