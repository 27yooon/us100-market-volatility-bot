#!/usr/bin/env python3
"""
Run two paper-trading strategies continuously for Render Background Worker.

No real orders are placed. Telegram notifications are optional and use Render env vars.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import market_signal_bot as bot
import notion_trade_logger


LOG_DIR = bot.PROJECT_DIR / "logs"
STATE_PATH = LOG_DIR / "render_dual_paper_state.json"
JSONL_PATH = LOG_DIR / "render_dual_paper_events.jsonl"

STRATEGY_VERSIONS = {
    "zukkumi_original": "zukkumi_original_v4",
    "indicator_basic": "indicator_basic_v1",
    "orb_paper": "orb_paper_v1",
    "score_watch": "score_watch_v2_paper_a_only",
}

PAPER_TRADE_STRATEGIES = {"zukkumi_original", "indicator_basic", "orb_paper", "score_watch"}
SCORE_WATCH_TRADE_MIN_SCORE = 75
SCORE_WATCH_TRADE_MIN_RR = 1.30
SCORE_WATCH_TRADE_MAX_RISK_POINTS = 40.0
SCORE_WATCH_TRADE_SESSIONS = {"EUROPE_TO_US_PRE", "US_PREMARKET", "US_REGULAR"}

LEGACY_STRATEGY_NAMES = {
    "zukkumi_rules": "zukkumi_original",
    "public_indicator_rules": "indicator_basic",
    "ny_orb_observation_rules": "orb_paper",
    "score_indicator_rules": "score_watch",
    "orb_watch": "orb_paper",
}


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
    strategy_version: str | None = None
    score_total: int | None = None
    score_breakdown: dict[str, Any] | None = None
    quality_tier: str | None = None


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


def local_dt(unix_ts: int) -> datetime:
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc).astimezone(bot.KST)


def ny_session_date(unix_ts: int) -> datetime.date:
    local = local_dt(unix_ts)
    if local.hour < 5:
        local = local - timedelta(days=1)
    return local.date()


def kst_date_from_text(value: Any) -> str:
    text = str(value or "")
    return text[:10] if len(text) >= 10 else ""


def session_date_from_trade(trade: dict[str, Any]) -> str:
    ts = trade.get("opened_at") or trade.get("closed_at")
    if isinstance(ts, (int, float)):
        return ny_session_date(int(ts)).isoformat()
    opened = kst_date_from_text(trade.get("opened_at_text"))
    return opened


def strategy_version(strategy: str) -> str:
    return STRATEGY_VERSIONS.get(strategy, strategy)


def quality_tier(score: int | None) -> str | None:
    if score is None:
        return None
    if score >= 75:
        return "A"
    if score >= 60:
        return "B"
    return "C"


def score_watch_follow_grade(signal: PaperSignal) -> str | None:
    if signal.observation_type != "SCORE_OBSERVATION" or signal.score_total is None:
        return None
    rr = signal.rr or 0.0
    if signal.score_total >= 75 and signal.level >= 2 and rr >= 1.30:
        return "A"
    if signal.score_total >= 60 and rr >= 1.00:
        return "B"
    if signal.score_total >= 55:
        return "C"
    return None


def score_watch_follow_note(grade: str | None) -> str:
    return {
        "A": "A급 검증 후보: 점수/방향/손익비가 모두 비교적 양호해 Render 모의매매 후보로 추적",
        "B": "B급 검증 후보: 일부 반대 신호를 허용하고 모의 데이터 확보용으로 추적",
        "C": "C급 관찰 후보: 방향이 애매하거나 손익비가 약해 진입보다 5/15/30분 후행 검증용",
    }.get(str(grade), "등급 미정 관찰 후보")


def strategy_display_name(name: str | None) -> str:
    return {
        "zukkumi_original": "쭈꾸미 원본",
        "indicator_basic": "기본지표",
        "orb_paper": "오픈박스 매매",
        "score_watch": "점수제 매매",
    }.get(str(name), str(name or "-"))


def short_reasons(record: dict[str, Any], limit: int = 3) -> str:
    reasons = record.get("reasons") or []
    if not isinstance(reasons, list):
        return str(reasons)[:300]
    return " / ".join(str(reason) for reason in reasons[:limit]) or "-"


def format_trade_telegram(record: dict[str, Any]) -> str:
    strategy = strategy_display_name(record.get("strategy"))
    event = record.get("event")
    if event == "OPEN":
        return "\n".join(
            [
                "[쭈꾸미 모의매매 진입]",
                f"전략: {strategy}",
                f"방향: {record.get('side')}",
                f"셋업: {record.get('setup_type')}",
                f"진입가: {float(record.get('entry', 0.0)):.2f}",
                f"목표가: {float(record.get('target', 0.0)):.2f}",
                f"무효/손절: {float(record.get('stop', 0.0)):.2f}",
                f"RR: {float(record.get('rr') or 0.0):.2f}",
                f"근거: {short_reasons(record)}",
                f"시각: {record.get('opened_at_text') or record.get('logged_at')}",
                "실거래 아님. Render 모의매매 기록.",
            ]
        )
    return "\n".join(
        [
            "[쭈꾸미 모의매매 청산]",
            f"전략: {strategy}",
            f"방향: {record.get('side')}",
            f"결과: {record.get('result')}",
            f"진입가: {float(record.get('entry', 0.0)):.2f}",
            f"청산가: {float(record.get('exit_price', 0.0)):.2f}",
            f"손익: {float(record.get('pnl_points', 0.0)):+.2f}pt",
            f"사유: {record.get('close_reason') or '-'}",
            f"진입: {record.get('opened_at_text')}",
            f"청산: {record.get('closed_at_text')}",
        ]
    )


def append_event(record: dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    record = {"logged_at": now_text(), **record}
    with JSONL_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps(record, ensure_ascii=False), flush=True)
    if record.get("event") == "HEARTBEAT" and record.get("today_status"):
        print(format_today_status_line(record["today_status"]), flush=True)
    send_telegram_for_event(record)
    if should_send_to_notion(record) and notion_trade_logger.enabled():
        notion_trade_logger.send(record)


def should_send_to_notion(record: dict[str, Any]) -> bool:
    return record.get("event") in {"OPEN", "CLOSE", "DAILY_REPORT", "ERROR"}


def telegram_enabled() -> bool:
    if str_bool_env("TELEGRAM_PAPER_NOTIFY", default=True) is False:
        return False
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"))


def str_bool_env(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def send_telegram_for_event(record: dict[str, Any]) -> None:
    event = record.get("event")
    text: str | None = None
    if event in {"OPEN", "CLOSE"} and record.get("strategy") in PAPER_TRADE_STRATEGIES:
        text = format_trade_telegram(record)
    elif event == "DAILY_REPORT":
        text = format_daily_report_telegram(record)
    if not text:
        return
    if not telegram_enabled():
        print("telegram_skipped: not_configured_or_disabled", flush=True)
        return
    ok, detail = bot.send_telegram_message(text)
    print(f"telegram_{event.lower()}={'ok' if ok else 'failed'}: {detail[:300]}", flush=True)


def initial_strategy_state(name: str | None = None) -> dict[str, Any]:
    return {
        "open_trade": None,
        "closed_trades": [],
        "seen_signal_keys": [],
        "watch_candidates": [],
        "seen_candidate_keys": [],
        "strategy_version": strategy_version(name or ""),
    }


def ensure_strategy_state(state: dict[str, Any]) -> None:
    strategies = state.setdefault("strategies", {})
    for old_name, new_name in LEGACY_STRATEGY_NAMES.items():
        if old_name in strategies and new_name not in strategies:
            strategies[new_name] = strategies.pop(old_name)
        elif old_name in strategies and new_name in strategies:
            old_state = strategies.pop(old_name)
            strategies[new_name]["closed_trades"] = [
                *old_state.get("closed_trades", []),
                *strategies[new_name].get("closed_trades", []),
            ][-500:]
            strategies[new_name]["watch_candidates"] = [
                *old_state.get("watch_candidates", []),
                *strategies[new_name].get("watch_candidates", []),
            ][-200:]
            strategies[new_name]["seen_signal_keys"] = [
                *old_state.get("seen_signal_keys", []),
                *strategies[new_name].get("seen_signal_keys", []),
            ][-300:]
            strategies[new_name]["seen_candidate_keys"] = [
                *old_state.get("seen_candidate_keys", []),
                *strategies[new_name].get("seen_candidate_keys", []),
            ][-500:]
    for name in STRATEGY_VERSIONS:
        if name not in strategies:
            strategies[name] = initial_strategy_state(name)
        strategies[name].setdefault("watch_candidates", [])
        strategies[name].setdefault("seen_candidate_keys", [])
        strategies[name]["strategy_version"] = strategy_version(name)


def load_state(reset: bool) -> dict[str, Any]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if reset:
        for path in (STATE_PATH, JSONL_PATH):
            if path.exists():
                path.unlink()
    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        ensure_strategy_state(state)
        return state
    state = {
        "session_started_at": now_text(),
        "mode": "render_dual_paper",
        "strategies": {
            "zukkumi_original": initial_strategy_state("zukkumi_original"),
            "indicator_basic": initial_strategy_state("indicator_basic"),
            "orb_paper": initial_strategy_state("orb_paper"),
            "score_watch": initial_strategy_state("score_watch"),
        },
    }
    ensure_strategy_state(state)
    return state


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


def macd_histogram(values: list[float], fast_n: int = 12, slow_n: int = 26, signal_n: int = 9) -> float | None:
    if len(values) < slow_n + signal_n:
        return None
    fast_values = ema(values, fast_n)
    slow_values = ema(values, slow_n)
    macd_values = [fast - slow for fast, slow in zip(fast_values, slow_values)]
    signal_values = ema(macd_values, signal_n)
    return macd_values[-1] - signal_values[-1]


def stochastic_k(bars: list[bot.Bar], n: int = 14) -> float | None:
    if len(bars) < n:
        return None
    recent = bars[-n:]
    low = min(bar.low for bar in recent)
    high = max(bar.high for bar in recent)
    if high <= low:
        return None
    return ((bars[-1].close - low) / (high - low)) * 100


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
    if "라운딩" not in candidate.setup_type:
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
    score_total: int | None = None,
    score_breakdown: dict[str, Any] | None = None,
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
        score_total=score_total,
        score_breakdown=score_breakdown,
        quality_tier=quality_tier(score_total),
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


def score_indicator_observation_candidates(bars: list[bot.Bar]) -> list[PaperSignal]:
    if len(bars) < 90:
        return []

    closes = [bar.close for bar in bars]
    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    ema200 = ema(closes, 200) if len(closes) >= 200 else []
    current_rsi = rsi(closes, 14)
    current_atr = atr(bars, 14)
    bands = bollinger(closes, 20)
    macd_hist = macd_histogram(closes)
    stoch = stochastic_k(bars, 14)
    if current_rsi is None or current_atr is None or bands is None or macd_hist is None or stoch is None:
        return []

    last = bars[-1]
    prev = bars[-2]
    mid, upper, lower = bands
    recent = bars[-8:]
    recent_low = min(bar.low for bar in recent)
    recent_high = max(bar.high for bar in recent)
    body = abs(last.close - last.open)
    candle_range = max(last.high - last.low, 0.01)
    chase_candle = body > current_atr * 1.2 or candle_range > current_atr * 1.8
    session = session_label(last.ts)
    out: list[PaperSignal] = []

    def build_score(side: str) -> tuple[int, dict[str, Any], list[str], list[str]]:
        score = 0
        breakdown: dict[str, Any] = {}
        reasons: list[str] = []
        cautions: list[str] = []

        trend_ok = ema20[-1] >= ema50[-1] if side == "LONG" else ema20[-1] <= ema50[-1]
        breakdown["ema20_50"] = 20 if trend_ok else 0
        score += breakdown["ema20_50"]
        reasons.append("EMA20/50 방향 일치" if trend_ok else "EMA20/50 방향 불일치")

        if ema200:
            long_term_ok = last.close >= ema200[-1] if side == "LONG" else last.close <= ema200[-1]
            breakdown["ema200"] = 10 if long_term_ok else 0
            score += breakdown["ema200"]
            if long_term_ok:
                reasons.append("EMA200 기준 방향 우위")

        if side == "LONG":
            boll_ok = last.close <= mid or any(bar.low <= lower for bar in recent)
            rsi_ok = current_rsi <= 55
            macd_ok = macd_hist >= 0
            stoch_ok = stoch <= 65
        else:
            boll_ok = last.close >= mid or any(bar.high >= upper for bar in recent)
            rsi_ok = current_rsi >= 45
            macd_ok = macd_hist <= 0
            stoch_ok = stoch >= 35

        breakdown["bollinger_position"] = 15 if boll_ok else 0
        breakdown["rsi"] = 15 if rsi_ok else 0
        breakdown["macd"] = 15 if macd_ok else 0
        breakdown["stochastic"] = 10 if stoch_ok else 0
        score += breakdown["bollinger_position"] + breakdown["rsi"] + breakdown["macd"] + breakdown["stochastic"]

        if boll_ok:
            reasons.append("Bollinger 위치가 진입 방향과 크게 충돌하지 않음")
        else:
            cautions.append("Bollinger 위치 불리")
        if rsi_ok:
            reasons.append(f"RSI14 {current_rsi:.1f} 허용")
        else:
            cautions.append(f"RSI14 {current_rsi:.1f} 불리")
        if macd_ok:
            reasons.append("MACD histogram 방향 일치")
        else:
            cautions.append("MACD histogram 방향 불일치")
        if stoch_ok:
            reasons.append(f"Stochastic {stoch:.1f} 허용")
        else:
            cautions.append(f"Stochastic {stoch:.1f} 불리")

        session_ok = session in {"US_PREMARKET", "US_REGULAR", "EUROPE_TO_US_PRE"}
        breakdown["session"] = 10 if session_ok else 0
        score += breakdown["session"]
        if session_ok:
            reasons.append(f"거래 관찰 세션 {session}")
        else:
            cautions.append(f"비활성 세션 {session}")

        volatility_ok = current_atr >= 8 and not chase_candle
        breakdown["atr_chase_filter"] = 15 if volatility_ok else 0
        score += breakdown["atr_chase_filter"]
        if volatility_ok:
            reasons.append(f"ATR14 {current_atr:.1f}, 추격 장대 아님")
        else:
            cautions.append(f"ATR/장대 필터 주의 ATR14 {current_atr:.1f}")

        breakdown["total"] = score
        return score, breakdown, reasons, cautions

    for side in ("LONG", "SHORT"):
        score, breakdown, reasons, cautions = build_score(side)
        if score < 55:
            continue
        if side == "LONG":
            stop = min(recent_low - current_atr * 0.2, last.close - max(20.0, current_atr * 1.1))
            setup = "점수제 지표 관찰 롱"
        else:
            stop = max(recent_high + current_atr * 0.2, last.close + max(20.0, current_atr * 1.1))
            setup = "점수제 지표 관찰 숏"
        signal = build_observation_signal(
            side,
            setup,
            2 if score >= 70 else 1,
            last.close,
            stop,
            last.ts,
            [f"점수제 공개지표 {score}/100", *reasons],
            cautions,
            "SCORE_OBSERVATION",
            score_total=score,
            score_breakdown=breakdown,
        )
        if signal is not None:
            grade = score_watch_follow_grade(signal)
            breakdown["follow_grade"] = grade
            signal = replace(
                signal,
                observation_type=f"SCORE_FOLLOW_{grade}" if grade else "SCORE_OBSERVATION",
                quality_tier=grade,
                score_breakdown=breakdown,
                reasons=[score_watch_follow_note(grade), *signal.reasons],
                cautions=[
                    *signal.cautions,
                    "score_watch_follow는 Render 모의매매 검증용이며 실거래 신호가 아님",
                ],
            )
            out.append(signal)

    return out[:2]


def score_indicator_trade_signal(bars: list[bot.Bar], min_rr: float) -> tuple[PaperSignal | None, list[PaperSignal]]:
    candidates = score_indicator_observation_candidates(bars)
    if not candidates:
        return None, []

    qualified: list[PaperSignal] = []
    for signal in candidates:
        if signal.quality_tier != "A":
            continue
        if (signal.score_total or 0) < SCORE_WATCH_TRADE_MIN_SCORE:
            continue
        if (signal.rr or 0.0) < max(min_rr, SCORE_WATCH_TRADE_MIN_RR):
            continue
        risk = abs(signal.entry - signal.stop)
        if risk > SCORE_WATCH_TRADE_MAX_RISK_POINTS:
            continue
        if session_label(signal.bar_time) not in SCORE_WATCH_TRADE_SESSIONS:
            continue
        qualified.append(signal)

    if not qualified:
        return None, candidates

    best = max(qualified, key=lambda item: ((item.score_total or 0), item.rr or 0.0, -abs(item.entry - item.stop)))
    return replace(
        best,
        setup_type=best.setup_type.replace("관찰", "A급 모의매매"),
        observation_type=None,
        reasons=[
            "score_watch A급 조건 통과: Render 모의매매 진입",
            *best.reasons,
        ],
        cautions=[
            caution for caution in best.cautions
            if "실전 진입 신호가 아님" not in caution
        ],
    ), candidates


def ny_orb_observation_candidates(bars: list[bot.Bar]) -> list[PaperSignal]:
    if len(bars) < 80:
        return []

    last = bars[-1]
    last_local = local_dt(last.ts)
    minutes = last_local.hour * 60 + last_local.minute
    if not (minutes >= 23 * 60 or minutes < 5 * 60):
        return []

    session_day = ny_session_date(last.ts)
    orb_bars = [
        bar for bar in bars
        if ny_session_date(bar.ts) == session_day and 22 * 60 + 30 <= local_dt(bar.ts).hour * 60 + local_dt(bar.ts).minute < 23 * 60
    ]
    if len(orb_bars) < 4:
        return []

    current_atr = atr(bars, 14)
    if current_atr is None or current_atr <= 0:
        return []

    orb_high = max(bar.high for bar in orb_bars)
    orb_low = min(bar.low for bar in orb_bars)
    orb_mid = (orb_high + orb_low) / 2
    orb_width = orb_high - orb_low
    if orb_width <= 0:
        return []

    recent = [bar for bar in bars if bar.ts > orb_bars[-1].ts][-8:]
    if not recent:
        return []

    closes = [bar.close for bar in bars]
    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    buffer = max(3.0, current_atr * 0.15)
    out: list[PaperSignal] = []
    width_ratio = orb_width / current_atr
    base_reasons = [
        f"NY 오픈 박스 22:30~23:00 KST high {orb_high:.2f} low {orb_low:.2f} mid {orb_mid:.2f}",
        f"박스폭 {orb_width:.1f}pt / ATR14 {current_atr:.1f} = {width_ratio:.2f}",
    ]
    base_cautions: list[str] = []
    if width_ratio < 0.35:
        base_cautions.append("박스폭이 ATR 대비 너무 좁아 가짜 돌파 주의")
    if width_ratio > 2.20:
        base_cautions.append("박스폭이 ATR 대비 너무 넓어 추격 금지 후보")

    broke_high = any(bar.high > orb_high + buffer for bar in recent)
    broke_low = any(bar.low < orb_low - buffer for bar in recent)
    closed_above = last.close > orb_high + buffer
    closed_below = last.close < orb_low - buffer
    back_inside_from_high = broke_high and last.close < orb_high
    back_inside_from_low = broke_low and last.close > orb_low
    near_mid = abs(last.close - orb_mid) <= max(5.0, current_atr * 0.25)

    def score_for(side: str, setup: str) -> tuple[int, dict[str, Any]]:
        trend_ok = ema20[-1] >= ema50[-1] if side == "LONG" else ema20[-1] <= ema50[-1]
        healthy_width = 0.35 <= width_ratio <= 2.20
        score = 35 + (20 if trend_ok else 0) + (20 if healthy_width else 0) + (15 if not (broke_high and broke_low) else 0) + (10 if session_label(last.ts) == "US_REGULAR" else 0)
        return score, {
            "orb_box": 35,
            "ema_alignment": 20 if trend_ok else 0,
            "atr_width": 20 if healthy_width else 0,
            "one_sided_break": 15 if not (broke_high and broke_low) else 0,
            "session": 10 if session_label(last.ts) == "US_REGULAR" else 0,
            "orb_high": round(orb_high, 2),
            "orb_low": round(orb_low, 2),
            "orb_mid": round(orb_mid, 2),
            "orb_width": round(orb_width, 2),
            "width_atr_ratio": round(width_ratio, 2),
            "setup": setup,
            "total": score,
        }

    cases: list[tuple[str, str, bool, float, list[str], list[str]]] = [
        ("LONG", "ORB 상단 돌파 관찰 롱", closed_above, orb_low - buffer, ["박스 상단 돌파 후 종가 유지"], []),
        ("SHORT", "ORB 하단 이탈 관찰 숏", closed_below, orb_high + buffer, ["박스 하단 이탈 후 종가 유지"], []),
        ("SHORT", "ORB 상단 돌파 실패 관찰 숏", back_inside_from_high, orb_high + buffer, ["상단 돌파 실패 후 박스 안 복귀"], []),
        ("LONG", "ORB 하단 이탈 실패 관찰 롱", back_inside_from_low, orb_low - buffer, ["하단 이탈 실패 후 박스 안 복귀"], []),
    ]
    if near_mid and (broke_high or broke_low):
        side = "LONG" if broke_low and not broke_high else "SHORT" if broke_high and not broke_low else ""
        if side:
            stop = orb_low - buffer if side == "LONG" else orb_high + buffer
            cases.append((side, "ORB 중간값 재테스트 관찰 " + ("롱" if side == "LONG" else "숏"), True, stop, ["박스 돌파/실패 후 중간값 재테스트"], ["방향 재확인 필요"]))

    for side, setup, condition, stop, reasons, cautions in cases:
        if not condition:
            continue
        score, breakdown = score_for(side, setup)
        signal = build_observation_signal(
            side,
            setup,
            2 if score >= 70 else 1,
            last.close,
            stop,
            last.ts,
            [*base_reasons, *reasons],
            [*base_cautions, *cautions],
            "ORB_OBSERVATION",
            score_total=score,
            score_breakdown=breakdown,
        )
        if signal is not None:
            out.append(signal)

    return out[:3]


def orb_paper_signal(bars: list[bot.Bar], min_rr: float) -> tuple[PaperSignal | None, list[PaperSignal]]:
    candidates = ny_orb_observation_candidates(bars)
    if not candidates:
        return None, []

    qualified = [
        signal for signal in candidates
        if (signal.score_total or 0) >= 70 and signal.level >= 2 and (signal.rr or 0) >= min_rr
    ]
    if not qualified:
        return None, candidates

    best = max(qualified, key=lambda signal: ((signal.score_total or 0), signal.rr or 0))
    setup_type = (
        best.setup_type
        .replace(" 관찰", "")
        .replace("ORB", "오픈박스")
    )
    reasons = [
        "오픈박스 매매 기준 통과",
        *best.reasons,
    ]
    cautions = [
        *best.cautions,
        "신규 검증용 세 번째 모의매매. 실거래 아님",
    ]
    return replace(
        best,
        setup_type=setup_type,
        reasons=reasons,
        cautions=cautions,
        observation_type=None,
        strategy_version=strategy_version("orb_paper"),
    ), candidates


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
    review_summary = "진입 보류 후보. 후행으로 +50pt 또는 무효 기준 선행 여부를 확인한다."
    if strategy == "score_watch":
        grade = signal.quality_tier or score_watch_follow_grade(signal)
        review_summary = (
            f"{score_watch_follow_note(grade)}. "
            "실제 진입이 아니라 후보 발생 후 5/15/30분 흐름, +50pt 목표, 무효 기준 선행 여부를 복기한다."
        )
    candidate = {
        "symbol": symbol,
        **asdict(signal),
        "strategy_version": signal.strategy_version or strategy_version(strategy),
        "candidate_status": status,
        "filter_reason": filter_reason,
        "observed_at": signal.bar_time,
        "observed_at_text": text_time(signal.bar_time),
        "signal_key": key,
        "review_summary": review_summary,
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
        "strategy_version": signal.strategy_version or strategy_version(strategy),
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
    typed_observations = sum(1 for candidate in candidates if candidate.get("observation_type"))
    return {
        "strategy_version": strategy_state.get("strategy_version"),
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "pnl_points": round(pnl, 2),
        "open": bool(strategy_state.get("open_trade")),
        "candidate_open": candidate_open,
        "missed_entries": missed,
        "filtered_ok": filtered_ok,
        "ambiguous": ambiguous,
        "observations": typed_observations or observation_count,
    }


def trade_date_text(trade: dict[str, Any], key: str) -> str:
    text = str(trade.get(key) or "")
    return text[:10] if len(text) >= 10 else ""


def today_status(strategies: dict[str, dict[str, Any]]) -> dict[str, Any]:
    today = datetime.now(bot.KST).strftime("%Y-%m-%d")
    per_strategy: dict[str, Any] = {}
    total_entries = 0
    total_closed = 0
    total_open = 0
    total_pnl = 0.0
    latest: list[dict[str, Any]] = []

    for name, strategy_state in strategies.items():
        open_trade_data = strategy_state.get("open_trade")
        open_today = bool(open_trade_data and trade_date_text(open_trade_data, "opened_at_text") == today)
        today_closed = [
            trade for trade in strategy_state.get("closed_trades", [])
            if trade_date_text(trade, "opened_at_text") == today or trade_date_text(trade, "closed_at_text") == today
        ]
        closed_count = len(today_closed)
        entries = closed_count + (1 if open_today else 0)
        wins = sum(1 for trade in today_closed if trade.get("result") == "WIN")
        losses = sum(1 for trade in today_closed if trade.get("result") == "LOSS")
        pnl = sum(float(trade.get("pnl_points", 0.0)) for trade in today_closed)

        total_entries += entries
        total_closed += closed_count
        total_open += 1 if open_today else 0
        total_pnl += pnl
        per_strategy[name] = {
            "entries": entries,
            "closed": closed_count,
            "open": open_today,
            "wins": wins,
            "losses": losses,
            "pnl_points": round(pnl, 2),
        }

        if open_today and open_trade_data:
            latest.append({
                "strategy": name,
                "status": "OPEN",
                "side": open_trade_data.get("side"),
                "setup": open_trade_data.get("setup_type"),
                "opened_at": open_trade_data.get("opened_at_text"),
                "entry": open_trade_data.get("entry"),
            })
        for trade in today_closed[-3:]:
            latest.append({
                "strategy": name,
                "status": trade.get("result"),
                "side": trade.get("side"),
                "setup": trade.get("setup_type"),
                "opened_at": trade.get("opened_at_text"),
                "closed_at": trade.get("closed_at_text"),
                "pnl_points": trade.get("pnl_points"),
            })

    latest.sort(key=lambda item: str(item.get("closed_at") or item.get("opened_at") or ""), reverse=True)
    label = "오늘 매매 없음"
    if total_entries:
        label = f"오늘 진입 {total_entries}회"
        if total_open:
            label += f", 보유 {total_open}건"
        if total_closed:
            label += f", 청산 {total_closed}건, 손익 {round(total_pnl, 2):+g}pt"

    return {
        "date": today,
        "label": label,
        "entries": total_entries,
        "closed": total_closed,
        "open": total_open,
        "pnl_points": round(total_pnl, 2),
        "strategies": per_strategy,
        "latest": latest[:5],
    }


def format_today_status_line(status: dict[str, Any]) -> str:
    strategy_parts = []
    for name, data in status.get("strategies", {}).items():
        strategy_parts.append(
            f"{name} 진입 {data.get('entries', 0)} / 보유 {int(bool(data.get('open')))} / 손익 {float(data.get('pnl_points', 0.0)):+.1f}pt"
        )
    return f"[TODAY_STATUS] {status.get('date')} {status.get('label')} | " + " | ".join(strategy_parts)


def report_due(now: datetime, report_type: str) -> bool:
    minutes = now.hour * 60 + now.minute
    if report_type == "MID_2300":
        return now.weekday() in {0, 1, 2, 3, 4} and 23 * 60 <= minutes < 24 * 60
    if report_type == "FINAL_0610":
        return now.weekday() in {1, 2, 3, 4, 5} and 6 * 60 + 10 <= minutes < 12 * 60
    return False


def report_date(now: datetime, report_type: str) -> str:
    if report_type == "FINAL_0610":
        return (now - timedelta(days=1)).date().isoformat()
    return now.date().isoformat()


def loss_review_item(strategy: str, trade: dict[str, Any]) -> dict[str, Any]:
    rr = float(trade.get("rr") or 0.0)
    level = int(trade.get("level") or 0)
    risk = abs(float(trade.get("entry", 0.0)) - float(trade.get("stop", 0.0)))
    score = trade.get("score_total")
    cautions = trade.get("cautions") or []
    if not isinstance(cautions, list):
        cautions = [str(cautions)]

    acceptable = rr >= 1.30 and level >= 2
    notes: list[str] = []
    if acceptable:
        notes.append("기본 진입 기준 통과")
    else:
        notes.append("기본 기준 약함")
    if strategy == "score_watch" and score is not None:
        notes.append(f"점수 {int(score)}")
        acceptable = acceptable and int(score) >= SCORE_WATCH_TRADE_MIN_SCORE and risk <= SCORE_WATCH_TRADE_MAX_RISK_POINTS
    if risk:
        notes.append(f"위험폭 {risk:.1f}pt")
    if cautions:
        notes.append("주의 " + " / ".join(str(item) for item in cautions[:2]))

    return {
        "strategy": strategy,
        "side": trade.get("side"),
        "setup": trade.get("setup_type"),
        "opened_at": trade.get("opened_at_text"),
        "closed_at": trade.get("closed_at_text"),
        "entry": trade.get("entry"),
        "exit_price": trade.get("exit_price"),
        "pnl_points": round(float(trade.get("pnl_points", 0.0)), 2),
        "rr": rr,
        "verdict": "충분히 진입 가능" if acceptable else "기준 약함/확인 필요",
        "reason": ", ".join(notes),
    }


def build_daily_report(
    strategies: dict[str, dict[str, Any]],
    report_type: str,
    report_date_text: str,
    symbol: str,
    price: float | None,
) -> dict[str, Any]:
    strategy_rows: dict[str, Any] = {}
    latest: list[dict[str, Any]] = []
    loss_reviews: list[dict[str, Any]] = []
    totals = {"entries": 0, "closed": 0, "open": 0, "wins": 0, "losses": 0, "pnl_points": 0.0}

    for name, strategy_state in strategies.items():
        open_trade_data = strategy_state.get("open_trade")
        open_in_session = bool(open_trade_data and session_date_from_trade(open_trade_data) == report_date_text)
        closed = [
            trade for trade in strategy_state.get("closed_trades", [])
            if session_date_from_trade(trade) == report_date_text
        ]
        candidates = [
            candidate for candidate in strategy_state.get("watch_candidates", [])
            if trade_date_text(candidate, "observed_at_text") == report_date_text
        ]
        wins = sum(1 for trade in closed if trade.get("result") == "WIN")
        losses = sum(1 for trade in closed if trade.get("result") == "LOSS")
        pnl = sum(float(trade.get("pnl_points", 0.0)) for trade in closed)
        entries = len(closed) + (1 if open_in_session else 0)
        missed_entries = sum(1 for candidate in candidates if candidate.get("candidate_result") == "MISSED_ENTRY")
        filtered_ok = sum(1 for candidate in candidates if candidate.get("candidate_result") == "FILTERED_OK")
        ambiguous = sum(1 for candidate in candidates if candidate.get("candidate_result") == "AMBIGUOUS")
        row = {
            "mode": "paper_trade",
            "entries": entries,
            "closed": len(closed),
            "open": open_in_session,
            "wins": wins,
            "losses": losses,
            "pnl_points": round(pnl, 2),
            "candidate_open": sum(1 for candidate in candidates if not candidate.get("candidate_result")),
            "missed_entries": missed_entries,
            "filtered_ok": filtered_ok,
            "ambiguous": ambiguous,
            "candidate_reviewed": missed_entries + filtered_ok + ambiguous,
        }
        strategy_rows[name] = row
        totals["entries"] += entries
        totals["closed"] += len(closed)
        totals["open"] += 1 if open_in_session else 0
        totals["wins"] += wins
        totals["losses"] += losses
        totals["pnl_points"] += pnl

        if open_in_session and open_trade_data:
            latest.append({
                "strategy": name,
                "status": "OPEN",
                "side": open_trade_data.get("side"),
                "setup": open_trade_data.get("setup_type"),
                "opened_at": open_trade_data.get("opened_at_text"),
                "entry": open_trade_data.get("entry"),
            })
        for trade in closed[-5:]:
            latest.append({
                "strategy": name,
                "status": trade.get("result"),
                "side": trade.get("side"),
                "setup": trade.get("setup_type"),
                "opened_at": trade.get("opened_at_text"),
                "closed_at": trade.get("closed_at_text"),
                "pnl_points": trade.get("pnl_points"),
            })
        if report_type == "FINAL_0610":
            for trade in closed:
                if trade.get("result") == "LOSS":
                    loss_reviews.append(loss_review_item(name, trade))

    totals["pnl_points"] = round(float(totals["pnl_points"]), 2)
    latest.sort(key=lambda item: str(item.get("closed_at") or item.get("opened_at") or ""), reverse=True)
    title = "23시 중간 보고" if report_type == "MID_2300" else "미국장 마감 최종 보고"
    return {
        "event": "DAILY_REPORT",
        "report_type": report_type,
        "report_title": title,
        "report_date": report_date_text,
        "symbol": symbol,
        "price": price,
        "totals": totals,
        "strategies": strategy_rows,
        "latest": latest[:8],
        "loss_reviews": loss_reviews[:12],
    }


def format_daily_report_telegram(record: dict[str, Any]) -> str:
    totals = record.get("totals") or {}
    lines = [
        f"[쭈꾸미 {record.get('report_title')}]",
        f"기준일: {record.get('report_date')}",
        f"종목: {record.get('symbol')} / 현재가: {record.get('price')}",
        "",
        f"총 진입: {int(totals.get('entries', 0))}회",
        f"보유: {int(totals.get('open', 0))}건 / 청산: {int(totals.get('closed', 0))}건",
        f"승패: {int(totals.get('wins', 0))}승 {int(totals.get('losses', 0))}패",
        f"손익: {float(totals.get('pnl_points', 0.0)):+.2f}pt",
        "",
        "전략별:",
    ]
    for name, row in (record.get("strategies") or {}).items():
        display = strategy_display_name(name)
        line = (
            f"- {display}: 진입 {int(row.get('entries', 0))}, 보유 {int(bool(row.get('open')))}, "
            f"{int(row.get('wins', 0))}승 {int(row.get('losses', 0))}패, {float(row.get('pnl_points', 0.0)):+.1f}pt"
        )
        lines.append(line)
    loss_reviews = record.get("loss_reviews") or []
    if loss_reviews:
        lines.extend(["", "LOSS 복기:"])
        for item in loss_reviews[:5]:
            lines.append(
                f"- {strategy_display_name(item.get('strategy'))} {item.get('side')} "
                f"{float(item.get('pnl_points') or 0.0):+.1f}pt: {item.get('verdict')} "
                f"({item.get('reason')})"
            )
    latest = record.get("latest") or []
    if latest:
        lines.extend(["", "최근 거래:"])
        for item in latest[:5]:
            lines.append(
                f"- {strategy_display_name(item.get('strategy'))} {item.get('side')} {item.get('status')} "
                f"{float(item.get('pnl_points') or 0.0):+.1f}pt {item.get('setup') or ''}"
            )
    lines.append("")
    lines.append("실거래 아님. Render 모의매매 보고.")
    return "\n".join(lines)


def maybe_send_daily_reports(state: dict[str, Any], symbol: str, price: float | None) -> None:
    now = datetime.now(bot.KST)
    sent = state.setdefault("daily_reports_sent", [])
    for report_type in ("MID_2300", "FINAL_0610"):
        if not report_due(now, report_type):
            continue
        date_text = report_date(now, report_type)
        key = f"{report_type}:{date_text}"
        if key in sent:
            continue
        report = build_daily_report(state["strategies"], report_type, date_text, symbol, price)
        append_event(report)
        sent.append(key)
    state["daily_reports_sent"] = sent[-60:]


def run_tick(state: dict[str, Any], symbol: str, interval: str, range_name: str, min_rr: float) -> None:
    ensure_strategy_state(state)
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
        if name == "zukkumi_original":
            signal = zukkumi_signal(symbol, bars, pivots, context, min_level=2, min_rr=min_rr)
            observations = []
            strict_observation = zukkumi_observation_candidate(symbol, bars, pivots, context, observe_min_rr=0.50)
            if strict_observation is not None:
                observations.append(strict_observation)
            observations.extend(broad_zukkumi_observation_candidates(bars, pivots, context, min_rr=min_rr))
            trade_min_level = 2
        elif name == "indicator_basic":
            signal = public_indicator_signal(bars, min_level=3)
            observations = [signal] if signal is not None else []
            trade_min_level = 3
        elif name == "orb_paper":
            signal, observations = orb_paper_signal(bars, min_rr=min_rr)
            trade_min_level = 2
        elif name == "score_watch":
            signal, observations = score_indicator_trade_signal(bars, min_rr=min_rr)
            trade_min_level = 2
        else:
            signal = None
            observations = []
            trade_min_level = 99
        if signal is None:
            for observation in observations:
                open_candidate(
                    name,
                    strategy_state,
                    symbol,
                    observation,
                    status="OBSERVATION_CANDIDATE" if observation.observation_type else "NO_TRADE_CANDIDATE",
                    filter_reason=candidate_filter_reason(observation, trade_min_level=trade_min_level, trade_min_rr=min_rr),
                )
            continue
        key = signal_key(name, symbol, signal)
        if key in strategy_state.get("seen_signal_keys", []):
            continue
        open_trade(name, strategy_state, symbol, signal)

    price = bars[-1].close if bars else None
    maybe_send_daily_reports(state, symbol, price)
    append_event(
        {
            "event": "HEARTBEAT",
            "symbol": symbol,
            "price": price,
            "strategy_versions": STRATEGY_VERSIONS,
            "today_status": today_status(strategies),
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
    symbol = bot.normalize_symbol(args.symbol)

    state = load_state(args.reset)
    append_event(
        {
            "event": "START",
            "mode": "render_dual_paper",
            "symbol": symbol,
            "poll": args.poll,
            "telegram": "enabled_if_env_present",
            "strategy_versions": STRATEGY_VERSIONS,
        }
    )
    while True:
        try:
            run_tick(state, symbol, args.interval, args.range_name, args.min_rr)
        except Exception as exc:  # noqa: BLE001
            append_event({"event": "ERROR", "message": str(exc)})
        if args.once:
            break
        time.sleep(max(30, args.poll))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
