#!/usr/bin/env python3
"""
US100 market signal bot.

This is the next step after the simple volatility bot:
- Watch US100-like Nasdaq data.
- Combine pivot, Fibonacci pullback, impulse/exhaustion, failed breakout,
  volume/range contraction, trend context, and risk/reward.
- Send Telegram alerts only when the setup is strong enough.

The goal is not to promise profit. The goal is to reduce weak alerts and show
the exact reasons, invalidation level, and risk/reward for each candidate.
"""

from __future__ import annotations

import json
import math
import os
import re
import struct
import sys
import time
import zlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4
from xml.etree import ElementTree
from zoneinfo import ZoneInfo


PROJECT_DIR = Path(__file__).resolve().parent
ROOT = PROJECT_DIR.parent
AUTOTRADE_ENV = ROOT / "autotrade_mvp" / ".env"
STATE_FILE = PROJECT_DIR / "signal_state.json"
LOG_DIR = PROJECT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

KST = ZoneInfo("Asia/Seoul")
YAHOO_CHART_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"

DEFAULT_SYMBOL = "NQ=F"
DEFAULT_INTERVAL = "5m"
DEFAULT_RANGE = "5d"
DEFAULT_MIN_LEVEL = 3
DEFAULT_MIN_RR = 1.30
DEFAULT_POLL_SECONDS = 60
DEFAULT_HEARTBEAT_MINUTES = 10

CONTEXT_SYMBOLS: dict[str, str] = {
    "NQ": "NQ=F",
    "QQQ": "QQQ",
    "VIX": "^VIX",
    "DXY": "DX-Y.NYB",
    "US10Y": "^TNX",
    "WTI": "CL=F",
    "SOX": "^SOX",
}

NEWS_FEEDS = [
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^NDX,QQQ,NQ=F,NVDA,TSLA&region=US&lang=en-US",
    "https://www.investing.com/rss/news_25.rss",
]

NEWS_KEYWORDS = [
    "fed",
    "fomc",
    "powell",
    "inflation",
    "cpi",
    "pce",
    "ppi",
    "jobs",
    "payroll",
    "unemployment",
    "treasury",
    "yield",
    "dollar",
    "oil",
    "tariff",
    "china",
    "nvidia",
    "semiconductor",
    "ai",
    "israel",
    "iran",
    "ukraine",
    "war",
]

NEWS_TAG_RULES: list[tuple[str, tuple[str, ...], str]] = [
    (
        "연준/금리",
        ("fed", "fomc", "powell", "treasury", "yield"),
        "금리 민감 뉴스. 나스닥 급변이면 추격보다 확인 우선",
    ),
    (
        "물가",
        ("inflation", "cpi", "pce", "ppi"),
        "물가 뉴스. 금리 기대가 바뀌면 방향이 빠르게 이어질 수 있음",
    ),
    (
        "고용",
        ("jobs", "payroll", "unemployment"),
        "고용 뉴스. 장 초반 변동성과 가짜 돌파 주의",
    ),
    (
        "달러",
        ("dollar", "dxy"),
        "달러 관련 뉴스. 달러 강세면 기술주에는 부담 가능",
    ),
    (
        "유가",
        ("oil", "wti", "crude"),
        "유가 관련 뉴스. 인플레/지정학 리스크와 함께 확인",
    ),
    (
        "관세/무역",
        ("tariff", "trade", "china"),
        "관세나 중국 이슈. 뉴스성 급등락이면 반대매매 조심",
    ),
    (
        "반도체/AI",
        ("nvidia", "semiconductor", "ai"),
        "나스닥 주도주 뉴스. NQ 방향성에 직접 영향 가능",
    ),
    (
        "지정학",
        ("israel", "iran", "ukraine", "war"),
        "지정학 뉴스. 급변 시 진입 근거보다 위험 필터로 사용",
    ),
]


@dataclass(frozen=True)
class Bar:
    ts: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class MarketMove:
    label: str
    symbol: str
    close: float
    prev_close: float
    move_pct: float
    move_points: float
    direction: str


@dataclass(frozen=True)
class PivotLevels:
    pp: float
    r1: float
    r2: float
    s1: float
    s2: float


@dataclass(frozen=True)
class SignalCandidate:
    side: str
    setup_type: str
    level: int
    level_name: str
    decision: str
    score: int
    entry: float
    stop: float
    target1: float
    target2: float | None
    rr: float
    invalidation: str
    reasons: list[str]
    cautions: list[str]
    bar_time: int


@dataclass(frozen=True)
class WatchStatus:
    level: int
    level_name: str
    decision: str
    reasons: list[str]
    cautions: list[str]
    current_price: float
    bar_time: int


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


def fetch_chart(symbol: str, interval: str, range_name: str) -> dict[str, Any]:
    params = {"interval": interval, "range": range_name, "includePrePost": "true"}
    url = f"{YAHOO_CHART_BASE}/{symbol}?{urlencode(params)}"
    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        method="GET",
    )
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8", "replace"))


def parse_bars(payload: dict[str, Any]) -> list[Bar]:
    result = payload["chart"]["result"][0]
    timestamps = result.get("timestamp") or []
    quote = result["indicators"]["quote"][0]
    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []

    bars: list[Bar] = []
    for ts, open_, high, low, close, volume in zip(timestamps, opens, highs, lows, closes, volumes):
        if None in (ts, open_, high, low, close):
            continue
        bars.append(
            Bar(
                ts=int(ts),
                open=float(open_),
                high=float(high),
                low=float(low),
                close=float(close),
                volume=float(volume or 0),
            )
        )
    return bars


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(state: dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def append_log(record: dict[str, Any]) -> None:
    path = LOG_DIR / "market_signal_events.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def kst_time_string(unix_ts: int) -> str:
    dt = datetime.fromtimestamp(unix_ts, tz=timezone.utc).astimezone(KST)
    return dt.strftime("%Y-%m-%d %H:%M:%S KST")


def ema(values: list[float], length: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (length + 1.0)
    out = [values[0]]
    for value in values[1:]:
        out.append((value * alpha) + (out[-1] * (1.0 - alpha)))
    return out


def sma(values: list[float], length: int) -> list[float]:
    out: list[float] = []
    window_sum = 0.0
    for index, value in enumerate(values):
        window_sum += value
        if index >= length:
            window_sum -= values[index - length]
        denominator = min(index + 1, length)
        out.append(window_sum / denominator)
    return out


def atr(bars: list[Bar], length: int = 14) -> list[float]:
    if not bars:
        return []
    true_ranges: list[float] = []
    prev_close = bars[0].close
    for bar in bars:
        true_ranges.append(max(bar.high - bar.low, abs(bar.high - prev_close), abs(bar.low - prev_close)))
        prev_close = bar.close
    return sma(true_ranges, length)


def compute_pivots(symbol: str) -> PivotLevels | None:
    try:
        daily = parse_bars(fetch_chart(symbol, "1d", "10d"))
    except Exception:
        return None
    if len(daily) < 2:
        return None
    prev = daily[-2]
    pp = (prev.high + prev.low + prev.close) / 3.0
    r1 = 2.0 * pp - prev.low
    s1 = 2.0 * pp - prev.high
    r2 = pp + (prev.high - prev.low)
    s2 = pp - (prev.high - prev.low)
    return PivotLevels(pp=pp, r1=r1, r2=r2, s1=s1, s2=s2)


def nearest_level(price: float, levels: dict[str, float]) -> tuple[str, float, float]:
    name, level = min(levels.items(), key=lambda item: abs(price - item[1]))
    return name, level, abs(price - level)


def extract_latest_move(label: str, symbol: str) -> MarketMove | None:
    try:
        bars = parse_bars(fetch_chart(symbol, DEFAULT_INTERVAL, "2d"))
    except Exception:
        return None
    if len(bars) < 2 or bars[-2].close == 0:
        return None
    prev_close = bars[-2].close
    close = bars[-1].close
    move_points = close - prev_close
    move_pct = (move_points / prev_close) * 100.0
    direction = "UP" if move_points > 0 else "DOWN" if move_points < 0 else "FLAT"
    return MarketMove(label, symbol, close, prev_close, move_pct, move_points, direction)


def fetch_context_snapshot() -> list[MarketMove]:
    moves: list[MarketMove] = []
    for label, symbol in CONTEXT_SYMBOLS.items():
        move = extract_latest_move(label, symbol)
        if move is not None:
            moves.append(move)
    return moves


def fetch_relevant_headlines(limit: int = 4) -> list[str]:
    headlines: list[str] = []
    seen: set[str] = set()
    keyword_re = re.compile("|".join(re.escape(word) for word in NEWS_KEYWORDS), re.IGNORECASE)
    for feed_url in NEWS_FEEDS:
        try:
            request = Request(feed_url, headers={"User-Agent": "Mozilla/5.0"}, method="GET")
            with urlopen(request, timeout=10) as response:
                xml_text = response.read().decode("utf-8", "replace")
            root = ElementTree.fromstring(xml_text)
        except Exception:
            continue
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            if not title or title in seen:
                continue
            if keyword_re.search(title):
                headlines.append(title)
                seen.add(title)
            if len(headlines) >= limit:
                return headlines
    return headlines


def summarize_news_for_user(headlines: list[str]) -> list[str]:
    if not headlines:
        return ["주요 키워드 헤드라인 없음"]

    lower_headlines = [headline.lower() for headline in headlines]
    lines: list[str] = []
    used_labels: set[str] = set()
    for label, keywords, note in NEWS_TAG_RULES:
        count = sum(1 for headline in lower_headlines if any(keyword in headline for keyword in keywords))
        if count == 0:
            continue
        used_labels.add(label)
        lines.append(f"- {label}: 관련 뉴스 {count}개. {note}")

    if not lines:
        return ["- 관련 뉴스는 있으나 핵심 키워드가 약함. 차트 반응 우선"]

    if len(used_labels) >= 3:
        lines.append("- 여러 뉴스가 섞임: 방향 단정 금지, 차트 확인 우선")
    return lines[:5]


def summarize_news_tags(headlines: list[str]) -> str:
    if not headlines:
        return "특이 뉴스 없음"

    lower_headlines = [headline.lower() for headline in headlines]
    labels: list[str] = []
    for label, keywords, _ in NEWS_TAG_RULES:
        if any(any(keyword in headline for keyword in keywords) for headline in lower_headlines):
            labels.append(label)

    if not labels:
        return "뉴스 있음, 핵심 키워드 약함"
    if len(labels) > 3:
        return ", ".join(labels[:3]) + " 등"
    return ", ".join(labels)


def range_of(bar: Bar) -> float:
    return max(bar.high - bar.low, 0.0001)


def body_of(bar: Bar) -> float:
    return abs(bar.close - bar.open)


def volume_drying(bars: list[Bar]) -> bool:
    recent = [bar.volume for bar in bars[-4:] if bar.volume > 0]
    if len(recent) < 4:
        return False
    return recent[-1] < recent[-2] <= recent[-3] or recent[-1] < sum(recent[:-1]) / 3.0


def range_shrinking(bars: list[Bar]) -> bool:
    if len(bars) < 4:
        return False
    ranges = [range_of(bar) for bar in bars[-4:]]
    return ranges[-1] < ranges[-2] <= ranges[-3] or ranges[-1] < sum(ranges[:-1]) / 3.0


def failed_high_breakout(bars: list[Bar], lookback: int, buffer: float) -> bool:
    if len(bars) <= lookback + 1:
        return False
    recent_high = max(bar.high for bar in bars[-lookback - 1 : -1])
    last = bars[-1]
    return last.high >= recent_high - buffer and last.close < recent_high


def failed_low_breakdown(bars: list[Bar], lookback: int, buffer: float) -> bool:
    if len(bars) <= lookback + 1:
        return False
    recent_low = min(bar.low for bar in bars[-lookback - 1 : -1])
    last = bars[-1]
    return last.low <= recent_low + buffer and last.close > recent_low


def find_impulse(bars: list[Bar], atr_value: float, lookback: int = 36) -> tuple[str, int, int, float, float] | None:
    if len(bars) < 30 or atr_value <= 0:
        return None
    window = bars[-lookback:]
    lows = [(index, bar.low) for index, bar in enumerate(window)]
    highs = [(index, bar.high) for index, bar in enumerate(window)]
    low_index, low_value = min(lows, key=lambda item: item[1])
    high_index, high_value = max(highs, key=lambda item: item[1])
    distance = high_value - low_value
    if distance < atr_value * 2.0:
        return None
    if low_index < high_index:
        return "UP", len(bars) - lookback + low_index, len(bars) - lookback + high_index, low_value, high_value
    return "DOWN", len(bars) - lookback + high_index, len(bars) - lookback + low_index, high_value, low_value


def fib_zone_for_impulse(impulse: tuple[str, int, int, float, float]) -> dict[str, float]:
    direction, _, _, start_price, end_price = impulse
    move = abs(end_price - start_price)
    if direction == "UP":
        return {
            "Fib 38.2": end_price - move * 0.382,
            "Fib 50.0": end_price - move * 0.500,
            "Fib 61.8": end_price - move * 0.618,
        }
    return {
        "Fib 38.2": end_price + move * 0.382,
        "Fib 50.0": end_price + move * 0.500,
        "Fib 61.8": end_price + move * 0.618,
    }


def price_near_any(price: float, levels: dict[str, float], max_distance: float) -> tuple[bool, str, float]:
    if not levels:
        return False, "", 0.0
    name, level, distance = nearest_level(price, levels)
    return distance <= max_distance, name, level


def detect_bottom_base_long(
    bars: list[Bar],
    support_levels: dict[str, float],
    fast_ema: float,
    atr_value: float,
    buffer: float,
    touch_distance: float,
) -> tuple[float, float, list[str], str] | None:
    """Find the user's pattern: sharp low, sideways base, then wait for breakout."""
    if len(bars) < 35 or atr_value <= 0:
        return None

    for base_len in range(4, 11):
        if len(bars) < base_len + 10:
            continue

        base = bars[-base_len:]
        pre = bars[-base_len - 10 : -base_len]
        base_lows = [bar.low for bar in base]
        base_high = max(bar.high for bar in base)
        base_low = min(base_lows)
        base_range = base_high - base_low
        low_pos = base_lows.index(base_low)
        after_low = base[low_pos + 1 :]
        last = bars[-1]

        if low_pos > max(1, base_len // 2):
            continue
        if len(after_low) < 2:
            continue

        drop_into_base = max(bar.high for bar in pre) - base_low
        if drop_into_base < atr_value * 0.9:
            continue
        if base_range > atr_value * 1.8:
            continue

        lower_low_failed = min(bar.low for bar in after_low) >= base_low - buffer
        closes_defended = min(bar.close for bar in after_low) >= base_low + buffer * 0.25
        if not (lower_low_failed and closes_defended):
            continue

        pre_avg_range = sum(range_of(bar) for bar in pre[-6:]) / 6.0
        base_avg_range = sum(range_of(bar) for bar in base[-3:]) / 3.0
        base_is_quiet = base_avg_range <= max(atr_value * 1.05, pre_avg_range * 0.85)
        if not base_is_quiet:
            continue

        support_hits = [
            (name, value)
            for name, value in support_levels.items()
            if base_low - touch_distance <= value <= base_high + touch_distance
        ]
        if support_hits:
            support_name, support_value = min(
                support_hits,
                key=lambda item: min(abs(item[1] - base_low), abs(item[1] - base_high), abs(item[1] - last.close)),
            )
        else:
            near_support, support_name, support_value = price_near_any(base_low, support_levels, touch_distance)
            if not near_support:
                continue

        reasons = [
            "바닥 형성 후 횡보",
            "저점 재이탈 실패",
            "작은 봉으로 매도세 약화",
            f"주요 지지 {support_name} 근처({support_value:.2f})",
        ]
        if last.close >= fast_ema - atr_value * 0.15:
            reasons.append("EMA20 근처 회복")
        if volume_drying(bars):
            reasons.append("거래량 감소")

        entry_trigger = base_high
        stop = base_low - buffer
        return entry_trigger, stop, reasons, support_name

    return None


def detect_pivot_rebound_long(
    bars: list[Bar],
    pivots: PivotLevels | None,
    fast_ema: float,
    slow_ema: float,
    atr_value: float,
    buffer: float,
    touch_distance: float,
) -> tuple[float, float, list[str], list[str]] | None:
    """Find a faster P-line bounce before a full sideways base forms."""
    if pivots is None or len(bars) < 25 or atr_value <= 0:
        return None

    pp = pivots.pp
    recent = bars[-8:]
    touch_indexes = [
        index
        for index, bar in enumerate(recent)
        if bar.low <= pp + touch_distance and bar.high >= pp - touch_distance
    ]
    if not touch_indexes:
        return None

    last_touch = touch_indexes[-1]
    after_touch = recent[last_touch:]
    last = recent[-1]

    if any(bar.close < pp - buffer for bar in after_touch):
        return None
    if min(bar.low for bar in after_touch) > pp + touch_distance:
        return None
    if last.close <= pp + buffer:
        return None
    if last.close < fast_ema - atr_value * 0.15:
        return None
    if last.close - pp > atr_value * 2.4:
        return None

    recent_high = max(bar.high for bar in recent[-3:])
    entry_trigger = recent_high
    stop = min(min(bar.low for bar in after_touch), pp) - buffer
    if stop >= entry_trigger:
        return None

    reasons = [
        f"일봉 P라인 근접 후 회복({pp:.2f})",
        "P라인 아래 5분봉 확정 이탈 실패",
        "직전 눌림 후 다시 상승 시도",
    ]
    cautions: list[str] = []
    if fast_ema >= slow_ema:
        reasons.append("EMA 20/50 기준 상승 우위")
    else:
        cautions.append("EMA 20/50은 아직 하락 우위")
    if volume_drying(bars):
        reasons.append("거래량 감소 후 반등")

    return entry_trigger, stop, reasons, cautions


def detect_rounding_reversal(
    bars: list[Bar],
    atr_value: float,
    buffer: float,
) -> tuple[str, float, float, list[str], list[str]] | None:
    """Find reversal bases that do not need a pivot touch."""
    if len(bars) < 45 or atr_value <= 0:
        return None

    for base_len in range(5, 11):
        if len(bars) < base_len + 14:
            continue

        base = bars[-base_len:]
        pre = bars[-base_len - 12 : -base_len]
        if len(pre) < 8:
            continue

        base_high = max(bar.high for bar in base)
        base_low = min(bar.low for bar in base)
        base_range = base_high - base_low
        pre_high = max(bar.high for bar in pre)
        pre_low = min(bar.low for bar in pre)
        pre_avg_range = sum(range_of(bar) for bar in pre[-6:]) / 6.0
        base_avg_range = sum(range_of(bar) for bar in base[-4:]) / 4.0

        if base_range > atr_value * 1.75:
            continue
        if base_avg_range > max(atr_value * 1.00, pre_avg_range * 0.82):
            continue

        base_lows = [bar.low for bar in base]
        base_highs = [bar.high for bar in base]
        low_pos = base_lows.index(base_low)
        high_pos = base_highs.index(base_high)
        last = base[-1]
        recent_ranges = [range_of(bar) for bar in base[-4:]]
        candle_shrink = recent_ranges[-1] <= max(atr_value * 0.95, sum(recent_ranges[:-1]) / 3.0)

        drop_into_base = pre_high - base_low
        if drop_into_base >= atr_value * 1.25 and low_pos <= max(2, base_len // 2):
            after_low = base[low_pos + 1 :]
            if len(after_low) >= 2:
                lower_low_failed = min(bar.low for bar in after_low) >= base_low - buffer
                close_defended = min(bar.close for bar in after_low) >= base_low + buffer * 0.10
                midpoint_recovered = last.close >= base_low + base_range * 0.45
                if lower_low_failed and close_defended and midpoint_recovered and candle_shrink:
                    reasons = [
                        "피봇 미터치 라운딩 바닥",
                        "하락 멈춤 후 봉 축소",
                        "저점 재이탈 실패",
                        "반대방향 확인봉 대기",
                    ]
                    cautions = ["피봇/주요 지지 터치 없는 역방향 시도"]
                    return "LONG", base_high, base_low - buffer, reasons, cautions

        rise_into_base = base_high - pre_low
        if rise_into_base >= atr_value * 1.25 and high_pos <= max(2, base_len // 2):
            after_high = base[high_pos + 1 :]
            if len(after_high) >= 2:
                higher_high_failed = max(bar.high for bar in after_high) <= base_high + buffer
                close_rejected = max(bar.close for bar in after_high) <= base_high - buffer * 0.10
                midpoint_lost = last.close <= base_high - base_range * 0.45
                if higher_high_failed and close_rejected and midpoint_lost and candle_shrink:
                    reasons = [
                        "피봇 미터치 라운딩 천장",
                        "상승 멈춤 후 봉 축소",
                        "고점 재돌파 실패",
                        "반대방향 확인봉 대기",
                    ]
                    cautions = ["피봇/주요 저항 터치 없는 역방향 시도"]
                    return "SHORT", base_low, base_high + buffer, reasons, cautions

    return None


def score_market_bias(context: list[MarketMove]) -> tuple[int, int, list[str]]:
    long_bias = 0
    short_bias = 0
    notes: list[str] = []
    by_label = {move.label: move for move in context}

    vix = by_label.get("VIX")
    dxy = by_label.get("DXY")
    us10y = by_label.get("US10Y")
    nq = by_label.get("NQ")

    if nq and nq.move_pct > 0:
        long_bias += 1
        notes.append("NQ 동반 상승")
    elif nq and nq.move_pct < 0:
        short_bias += 1
        notes.append("NQ 동반 하락")

    if vix and vix.move_pct < -0.5:
        long_bias += 1
        notes.append("VIX 하락")
    elif vix and vix.move_pct > 0.5:
        short_bias += 1
        notes.append("VIX 상승")

    if dxy and dxy.move_pct < -0.1:
        long_bias += 1
        notes.append("DXY 약세")
    elif dxy and dxy.move_pct > 0.1:
        short_bias += 1
        notes.append("DXY 강세")

    if us10y and us10y.move_points < -0.03:
        long_bias += 1
        notes.append("10년물 하락")
    elif us10y and us10y.move_points > 0.03:
        short_bias += 1
        notes.append("10년물 상승")

    return long_bias, short_bias, notes


def choose_targets(side: str, entry: float, pivots: PivotLevels | None, bars: list[Bar]) -> tuple[float, float | None]:
    recent_high = max(bar.high for bar in bars[-24:])
    recent_low = min(bar.low for bar in bars[-24:])
    if pivots is None:
        return (recent_high if side == "LONG" else recent_low), None

    levels = [pivots.s2, pivots.s1, pivots.pp, pivots.r1, pivots.r2, recent_low, recent_high]
    if side == "LONG":
        above = sorted(level for level in levels if level > entry)
        if not above:
            return recent_high, None
        return above[0], above[1] if len(above) > 1 else None
    below = sorted((level for level in levels if level < entry), reverse=True)
    if not below:
        return recent_low, None
    return below[0], below[1] if len(below) > 1 else None


def daily_pivot_context(
    side: str,
    entry: float,
    pivots: PivotLevels | None,
    touch_distance: float,
) -> tuple[list[str], list[str]]:
    if pivots is None:
        return [], ["일봉 피봇 확인 불가"]

    levels = {"P": pivots.pp, "R1": pivots.r1, "R2": pivots.r2, "S1": pivots.s1, "S2": pivots.s2}
    level_name, level_value, distance = nearest_level(entry, levels)
    near_daily_pivot = distance <= touch_distance
    reasons: list[str] = []
    cautions: list[str] = []

    if side == "LONG":
        if near_daily_pivot and level_name in {"S1", "S2", "P"}:
            reasons.append(f"일봉 피봇 지지 {level_name} 근처({level_value:.2f})")
        elif near_daily_pivot:
            cautions.append(f"일봉 피봇 {level_name} 근처라 롱 추격 주의")
        else:
            cautions.append("일봉 피봇 지지와 멀어 라운딩 단독 신뢰 낮음")

        if entry >= pivots.pp:
            reasons.append("일봉 P 위라 롱 방향 우위")
        else:
            cautions.append("일봉 P 아래라 롱은 역방향")
    else:
        if near_daily_pivot and level_name in {"R1", "R2", "P"}:
            reasons.append(f"일봉 피봇 저항 {level_name} 근처({level_value:.2f})")
        elif near_daily_pivot:
            cautions.append(f"일봉 피봇 {level_name} 근처라 숏 추격 주의")
        else:
            cautions.append("일봉 피봇 저항과 멀어 라운딩 단독 신뢰 낮음")

        if entry <= pivots.pp:
            reasons.append("일봉 P 아래라 숏 방향 우위")
        else:
            cautions.append("일봉 P 위라 숏은 역방향")

    return reasons, cautions


def rr_for(side: str, entry: float, stop: float, target: float) -> float:
    risk = entry - stop if side == "LONG" else stop - entry
    reward = target - entry if side == "LONG" else entry - target
    if risk <= 0 or reward <= 0:
        return 0.0
    return reward / risk


def level_name_for(level: int) -> str:
    if level >= 5:
        return "진입 금지"
    if level == 4:
        return "강한 후보"
    if level == 3:
        return "진입 후보"
    if level == 2:
        return "대기"
    return "보기만"


def decision_for(level: int, side: str | None = None) -> str:
    if level >= 5:
        return "건드리지 않기. 추격 또는 위험 구간"
    if level == 4 and side:
        return f"{side} 우선 확인. 손절/익절이 맞으면 진입 검토"
    if level == 3 and side:
        return f"{side} 진입 후보. 차트 보고 최종 확인"
    if level == 2:
        return "기다리기. 조건 형성 중이지만 아직 진입 아님"
    return "보기만. 아직 매매 자리 아님"


def next_action_for(level: int) -> str:
    if level >= 5:
        return "진입하지 말고 대기"
    if level == 4:
        return "차트 열고 진입/손절/익절 즉시 확인"
    if level == 3:
        return "차트 열고 확인 후 소액 또는 계획대로만 검토"
    if level == 2:
        return "차트는 봐도 되지만 아직 누르지 않기"
    return "아무것도 하지 말고 보기만"


def classify_level(score: int, rr: float, cautions: list[str], min_rr: float) -> int:
    effective_score = score - len(cautions)
    if effective_score >= 8 and rr >= max(1.60, min_rr):
        return 4
    if effective_score >= 5 and rr >= min_rr:
        return 3
    if effective_score >= 3:
        return 2
    return 1


def build_candidate(
    side: str,
    setup_type: str,
    entry: float,
    stop: float,
    target1: float,
    target2: float | None,
    bar_time: int,
    reasons: list[str],
    cautions: list[str],
    min_rr: float,
) -> SignalCandidate:
    score = len(reasons)
    rr = rr_for(side, entry, stop, target1)
    level = classify_level(score, rr, cautions, min_rr)
    return SignalCandidate(
        side=side,
        setup_type=setup_type,
        level=level,
        level_name=level_name_for(level),
        decision=decision_for(level, side),
        score=score,
        entry=entry,
        stop=stop,
        target1=target1,
        target2=target2,
        rr=rr,
        invalidation=(
            f"{stop:.2f} 아래 5분봉 마감" if side == "LONG" else f"{stop:.2f} 위 5분봉 마감"
        ),
        reasons=reasons,
        cautions=cautions,
        bar_time=bar_time,
    )


def build_pivot_rebound_confirmed(
    bars: list[Bar],
    pivots: PivotLevels | None,
    context: list[MarketMove],
    min_rr: float,
) -> SignalCandidate | None:
    if pivots is None or len(bars) < 80:
        return None

    closes = [bar.close for bar in bars]
    fast = ema(closes, 20)
    slow = ema(closes, 50)
    atr_value = atr(bars, 14)[-1]
    if atr_value <= 0:
        return None

    pp = pivots.pp
    buffer = atr_value * 0.20
    touch_distance = atr_value * 0.45
    recent = bars[-8:]
    last = recent[-1]
    touch_indexes = [
        index
        for index, bar in enumerate(recent[:-1])
        if bar.low <= pp + touch_distance and bar.high >= pp - touch_distance
    ]
    if not touch_indexes:
        return None

    last_touch = touch_indexes[-1]
    after_touch = recent[last_touch:]
    touch_low = min(bar.low for bar in after_touch)
    if any(bar.close < pp - buffer for bar in after_touch):
        return None
    if touch_low > pp + touch_distance:
        return None
    if last.close <= pp + buffer:
        return None
    if last.close <= pp + touch_distance:
        return None
    if last.close < fast[-1] - atr_value * 0.15:
        return None
    if last.close - pp > atr_value * 2.2:
        return None

    entry = last.close
    stop = touch_low - buffer
    target1 = entry + 50.0
    target2, _ = choose_targets("LONG", entry, pivots, bars)
    if target2 <= target1:
        target2 = None

    reasons = [
        f"일봉 P라인 근접 후 회복({pp:.2f})",
        "P라인 아래 5분봉 확정 이탈 실패",
        "회복봉이 직전 봉보다 높게 마감",
    ]
    cautions: list[str] = []
    if fast[-1] >= slow[-1]:
        reasons.append("EMA 20/50 기준 상승 우위")
    else:
        cautions.append("EMA 20/50은 아직 하락 우위")
    if volume_drying(bars):
        reasons.append("거래량 감소 후 반등")

    long_bias, short_bias, _ = score_market_bias(context)
    if long_bias > short_bias:
        reasons.append("시장 보조지표가 롱에 우호적")
    elif short_bias > long_bias + 1:
        cautions.append("시장 보조지표가 롱에 불리")

    candidate = build_candidate(
        "LONG",
        "P라인 반등 롱 확인",
        entry,
        stop,
        target1,
        target2,
        last.ts,
        reasons,
        cautions,
        min_rr,
    )
    if candidate.rr < min_rr:
        return None
    return candidate


def build_raw_candidate(
    bars: list[Bar],
    pivots: PivotLevels | None,
    context: list[MarketMove],
    min_rr: float,
) -> SignalCandidate | None:
    if len(bars) < 80:
        return None

    closes = [bar.close for bar in bars]
    fast = ema(closes, 20)
    slow = ema(closes, 50)
    atr_values = atr(bars, 14)
    last = bars[-1]
    atr_value = atr_values[-1]
    buffer = atr_value * 0.20
    touch_distance = atr_value * 0.45

    trend_long = fast[-1] >= slow[-1]
    trend_short = fast[-1] <= slow[-1]
    stretched_up = last.close > fast[-1] + atr_value * 1.8
    stretched_down = last.close < fast[-1] - atr_value * 1.8

    impulse = find_impulse(bars, atr_value)
    fib_levels = fib_zone_for_impulse(impulse) if impulse else {}

    pivot_levels: dict[str, float] = {}
    if pivots:
        pivot_levels = {"P": pivots.pp, "R1": pivots.r1, "R2": pivots.r2, "S1": pivots.s1, "S2": pivots.s2}

    recent_high = max(bar.high for bar in bars[-36:-1])
    recent_low = min(bar.low for bar in bars[-36:-1])
    structure_levels = {"전고점": recent_high, "전저점": recent_low, **pivot_levels}

    volume_is_drying = volume_drying(bars)
    range_is_shrinking = range_shrinking(bars)
    long_bias, short_bias, context_notes = score_market_bias(context)

    candidates: list[SignalCandidate] = []

    near_fib, fib_name, fib_level = price_near_any(last.close, fib_levels, touch_distance)
    near_level, level_name, level_value = price_near_any(last.close, structure_levels, touch_distance)

    support_levels = {name: value for name, value in structure_levels.items() if name in {"P", "S1", "S2", "전저점"}}
    pivot_rebound = detect_pivot_rebound_long(bars, pivots, fast[-1], slow[-1], atr_value, buffer, touch_distance)
    if pivot_rebound:
        entry_trigger, stop, reasons, cautions = pivot_rebound
        if long_bias > short_bias:
            reasons.append("시장 보조지표가 롱에 우호적")
        elif short_bias > long_bias + 1:
            cautions.append("시장 보조지표가 롱에 불리")

        target1 = entry_trigger + 50.0
        target2, _ = choose_targets("LONG", entry_trigger, pivots, bars)
        if target2 <= target1:
            target2 = None
        candidate = build_candidate(
            "LONG",
            "P라인 반등 롱",
            entry_trigger,
            stop,
            target1,
            target2,
            last.ts,
            reasons,
            cautions,
            min_rr,
        )
        if candidate.rr >= min_rr:
            candidates.append(candidate)

    bottom_base = detect_bottom_base_long(bars, support_levels, fast[-1], atr_value, buffer, touch_distance)
    if bottom_base:
        entry_trigger, stop, reasons, support_name = bottom_base
        setup_name = "P라인 바닥 횡보 롱" if support_name == "P" else "바닥 횡보 롱"
        if support_name == "P":
            reasons = ["P라인 터치/근접 후 횡보", *reasons]
        cautions: list[str] = []
        if trend_long:
            reasons.append("EMA 20/50 기준 상승 우위")
        elif last.close >= fast[-1] - atr_value * 0.15:
            reasons.append("EMA20 회복 시도")
        else:
            cautions.append("아직 EMA 20/50 하락 우위")
        if long_bias > short_bias:
            reasons.append("시장 보조지표가 롱에 우호적")
        elif short_bias > long_bias + 1:
            cautions.append("시장 보조지표가 롱에 불리")

        target1, target2 = choose_targets("LONG", entry_trigger, pivots, bars)
        candidate = build_candidate(
            "LONG",
            setup_name,
            entry_trigger,
            stop,
            target1,
            target2,
            last.ts,
            reasons,
            cautions,
            min_rr,
        )
        if candidate.rr >= min_rr:
            candidates.append(candidate)

    rounding = detect_rounding_reversal(bars, atr_value, buffer)
    if rounding:
        side, entry_trigger, stop, reasons, cautions = rounding
        if side == "LONG":
            setup_name = "라운딩 바닥 롱"
            if trend_long:
                reasons.append("EMA 20/50 기준 상승 우위")
            elif last.close >= fast[-1] - atr_value * 0.15:
                reasons.append("EMA20 회복 시도")
            else:
                cautions.append("아직 EMA 20/50 하락 우위")
            if long_bias > short_bias:
                reasons.append("시장 보조지표가 롱에 우호적")
            elif short_bias > long_bias + 1:
                cautions.append("시장 보조지표가 롱에 불리")
        else:
            setup_name = "라운딩 천장 숏"
            if trend_short:
                reasons.append("EMA 20/50 기준 하락 우위")
            elif last.close <= fast[-1] + atr_value * 0.15:
                reasons.append("EMA20 이탈 시도")
            else:
                cautions.append("아직 EMA 20/50 상승 우위")
            if short_bias > long_bias:
                reasons.append("시장 보조지표가 숏에 우호적")
            elif long_bias > short_bias + 1:
                cautions.append("시장 보조지표가 숏에 불리")

        if volume_is_drying:
            reasons.append("거래량 감소")

        pivot_reasons, pivot_cautions = daily_pivot_context(side, entry_trigger, pivots, touch_distance)
        reasons.extend(pivot_reasons)
        cautions.extend(pivot_cautions)

        target1, target2 = choose_targets(side, entry_trigger, pivots, bars)
        candidate = build_candidate(
            side,
            setup_name,
            entry_trigger,
            stop,
            target1,
            target2,
            last.ts,
            reasons,
            cautions,
            min_rr,
        )
        if candidate.rr >= min_rr:
            candidates.append(candidate)

    if impulse and impulse[0] == "UP":
        reasons: list[str] = ["상승 충격파 이후 눌림 구간"]
        cautions: list[str] = []
        if near_fib:
            reasons.append(f"{fib_name} 되돌림 근처({fib_level:.2f})")
        if near_level and level_name in {"P", "S1", "S2", "전저점"}:
            reasons.append(f"지지 후보 {level_name} 근처({level_value:.2f})")
        if trend_long:
            reasons.append("EMA 20/50 기준 상승 우위")
        if not stretched_up:
            reasons.append("장대봉 추격 구간 아님")
        else:
            cautions.append("상승 과열 구간이라 추격 주의")
        if volume_is_drying:
            reasons.append("거래량 감소")
        if range_is_shrinking:
            reasons.append("봉 크기 축소")
        if failed_low_breakdown(bars, 5, buffer):
            reasons.append("저점 이탈 실패 후 회복")
        if long_bias > short_bias:
            reasons.append("시장 보조지표가 롱에 우호적")
        elif short_bias > long_bias + 1:
            cautions.append("VIX/DXY/금리 쪽이 롱에 불리")

        stop = min(bar.low for bar in bars[-6:]) - buffer
        target1, target2 = choose_targets("LONG", last.close, pivots, bars)
        candidate = build_candidate("LONG", "피보 눌림 롱", last.close, stop, target1, target2, last.ts, reasons, cautions, min_rr)
        if near_fib and candidate.rr >= min_rr:
            candidates.append(candidate)

    if impulse and impulse[0] == "DOWN":
        reasons = ["하락 충격파 이후 반등 구간"]
        cautions = []
        if near_fib:
            reasons.append(f"{fib_name} 되돌림 근처({fib_level:.2f})")
        if near_level and level_name in {"P", "R1", "R2", "전고점"}:
            reasons.append(f"저항 후보 {level_name} 근처({level_value:.2f})")
        if trend_short:
            reasons.append("EMA 20/50 기준 하락 우위")
        if not stretched_down:
            reasons.append("장대봉 추격 구간 아님")
        else:
            cautions.append("하락 과열 구간이라 추격 주의")
        if volume_is_drying:
            reasons.append("거래량 감소")
        if range_is_shrinking:
            reasons.append("봉 크기 축소")
        if failed_high_breakout(bars, 5, buffer):
            reasons.append("고점 돌파 실패 후 하락")
        if short_bias > long_bias:
            reasons.append("시장 보조지표가 숏에 우호적")
        elif long_bias > short_bias + 1:
            cautions.append("VIX/DXY/금리 쪽이 숏에 불리")

        stop = max(bar.high for bar in bars[-6:]) + buffer
        target1, target2 = choose_targets("SHORT", last.close, pivots, bars)
        candidate = build_candidate("SHORT", "피보 반등 숏", last.close, stop, target1, target2, last.ts, reasons, cautions, min_rr)
        if near_fib and candidate.rr >= min_rr:
            candidates.append(candidate)

    # Exhaustion reversal setups: useful when a long run reaches a major level and fails.
    if impulse and impulse[0] == "UP" and near_level and level_name in {"R1", "R2", "전고점"}:
        reasons = [f"상승파 말단 저항 {level_name} 근처({level_value:.2f})"]
        cautions = []
        if failed_high_breakout(bars, 5, buffer):
            reasons.append("고점 돌파 실패")
        if volume_is_drying:
            reasons.append("거래량 감소")
        if range_is_shrinking:
            reasons.append("봉 크기 축소")
        if stretched_up:
            reasons.append("EMA 대비 과열 후 피로감")
        if short_bias >= long_bias:
            reasons.append("시장 보조지표가 숏을 막지 않음")
        else:
            cautions.append("시장 보조지표는 아직 상승 우위")
        stop = max(bar.high for bar in bars[-6:]) + buffer
        target1, target2 = choose_targets("SHORT", last.close, pivots, bars)
        candidate = build_candidate("SHORT", "상승 피로 숏", last.close, stop, target1, target2, last.ts, reasons, cautions, min_rr)
        if candidate.rr >= min_rr:
            candidates.append(candidate)

    if impulse and impulse[0] == "DOWN" and near_level and level_name in {"S1", "S2", "전저점"}:
        reasons = [f"하락파 말단 지지 {level_name} 근처({level_value:.2f})"]
        cautions = []
        if failed_low_breakdown(bars, 5, buffer):
            reasons.append("저점 이탈 실패")
        if volume_is_drying:
            reasons.append("거래량 감소")
        if range_is_shrinking:
            reasons.append("봉 크기 축소")
        if stretched_down:
            reasons.append("EMA 대비 과매도 후 피로감")
        if long_bias >= short_bias:
            reasons.append("시장 보조지표가 롱을 막지 않음")
        else:
            cautions.append("시장 보조지표는 아직 하락 우위")
        stop = min(bar.low for bar in bars[-6:]) - buffer
        target1, target2 = choose_targets("LONG", last.close, pivots, bars)
        candidate = build_candidate("LONG", "하락 피로 롱", last.close, stop, target1, target2, last.ts, reasons, cautions, min_rr)
        if candidate.rr >= min_rr:
            candidates.append(candidate)

    if not candidates:
        return None

    # Core reasons raise the rank; cautions lower it.
    return max(candidates, key=lambda candidate: (candidate.level, candidate.score - len(candidate.cautions), candidate.rr))


def confirm_candidate(
    raw: SignalCandidate,
    bars: list[Bar],
    pivots: PivotLevels | None,
    min_rr: float,
) -> SignalCandidate | None:
    if len(bars) < 2:
        return None

    setup_bar = bars[-2]
    confirm_bar = bars[-1]

    if raw.side == "LONG":
        if confirm_bar.close <= max(setup_bar.high, raw.entry):
            return None
        reasons = [*raw.reasons, "확인봉이 횡보 박스/후보봉 고가 위에서 마감"]
    else:
        if confirm_bar.close >= min(setup_bar.low, raw.entry):
            return None
        reasons = [*raw.reasons, "확인봉이 횡보 박스/후보봉 저가 아래에서 마감"]

    entry = confirm_bar.close
    target1, target2 = choose_targets(raw.side, entry, pivots, bars)
    if raw.side == "LONG" and raw.setup_type in {"P라인 반등 롱", "P라인 바닥 횡보 롱"}:
        target1 = max(target1, entry + 50.0)
        if target2 is not None and target2 <= target1:
            target2 = None
    confirmed = build_candidate(
        raw.side,
        f"{raw.setup_type} 확인",
        entry,
        raw.stop,
        target1,
        target2,
        confirm_bar.ts,
        reasons,
        raw.cautions,
        min_rr,
    )
    if confirmed.rr < min_rr:
        return None
    return confirmed


def analyze_signal(
    bars: list[Bar],
    pivots: PivotLevels | None,
    context: list[MarketMove],
    min_rr: float,
) -> SignalCandidate | None:
    if len(bars) < 81:
        return None

    direct = build_pivot_rebound_confirmed(bars, pivots, context, min_rr)
    if direct:
        return direct

    # First find a setup on the previous completed candle, then require the
    # latest candle to confirm direction. This removes many immediate failures.
    raw = build_raw_candidate(bars[:-1], pivots, context, min_rr)
    if raw is None:
        return None
    return confirm_candidate(raw, bars, pivots, min_rr)


def build_watch_status(
    bars: list[Bar],
    pivots: PivotLevels | None,
    context: list[MarketMove],
) -> WatchStatus:
    closes = [bar.close for bar in bars]
    fast = ema(closes, 20)
    slow = ema(closes, 50)
    atr_values = atr(bars, 14)
    last = bars[-1]
    atr_value = atr_values[-1]
    touch_distance = atr_value * 0.45
    buffer = atr_value * 0.20

    impulse = find_impulse(bars, atr_value)
    fib_levels = fib_zone_for_impulse(impulse) if impulse else {}
    pivot_levels: dict[str, float] = {}
    if pivots:
        pivot_levels = {"P": pivots.pp, "R1": pivots.r1, "R2": pivots.r2, "S1": pivots.s1, "S2": pivots.s2}

    recent_high = max(bar.high for bar in bars[-36:-1])
    recent_low = min(bar.low for bar in bars[-36:-1])
    structure_levels = {"전고점": recent_high, "전저점": recent_low, **pivot_levels}

    near_fib, fib_name, fib_level = price_near_any(last.close, fib_levels, touch_distance)
    near_level, level_name, level_value = price_near_any(last.close, structure_levels, touch_distance)
    stretched_up = last.close > fast[-1] + atr_value * 1.8
    stretched_down = last.close < fast[-1] - atr_value * 1.8
    volume_is_drying = volume_drying(bars)
    range_is_shrinking = range_shrinking(bars)
    failed_high = failed_high_breakout(bars, 5, buffer)
    failed_low = failed_low_breakdown(bars, 5, buffer)
    long_bias, short_bias, _ = score_market_bias(context)

    reasons: list[str] = []
    cautions: list[str] = []

    if impulse:
        reasons.append("상승 충격파 이후" if impulse[0] == "UP" else "하락 충격파 이후")
    else:
        reasons.append("뚜렷한 충격파 없음")
    if near_fib:
        reasons.append(f"{fib_name} 근처({fib_level:.2f})")
    if near_level:
        reasons.append(f"주요 레벨 {level_name} 근처({level_value:.2f})")
    if volume_is_drying:
        reasons.append("거래량 감소")
    if range_is_shrinking:
        reasons.append("봉 크기 축소")
    if failed_high:
        reasons.append("고점 돌파 실패")
    if failed_low:
        reasons.append("저점 이탈 실패")
    if fast[-1] >= slow[-1]:
        reasons.append("EMA 20/50 상승 우위")
    else:
        reasons.append("EMA 20/50 하락 우위")
    if long_bias > short_bias:
        reasons.append("시장 보조지표는 롱 우위")
    elif short_bias > long_bias:
        reasons.append("시장 보조지표는 숏 우위")

    if stretched_up:
        cautions.append("상승 장대 추격 위험")
    if stretched_down:
        cautions.append("하락 장대 추격 위험")

    setup_count = sum([near_fib, near_level, volume_is_drying, range_is_shrinking, failed_high or failed_low])
    if (stretched_up or stretched_down) and not near_fib and not near_level:
        level = 5
    elif setup_count >= 4:
        level = 2
    elif near_fib or near_level:
        level = 1
    else:
        level = 1

    return WatchStatus(
        level=level,
        level_name=level_name_for(level),
        decision=decision_for(level),
        reasons=reasons[:8],
        cautions=cautions,
        current_price=last.close,
        bar_time=last.ts,
    )


def format_context_line(move: MarketMove) -> str:
    arrow = "↑" if move.direction == "UP" else "↓" if move.direction == "DOWN" else "="
    if move.label == "US10Y":
        return f"{move.label}: {arrow} {move.move_points:+.2f}pt ({move.close:.2f})"
    return f"{move.label}: {arrow} {move.move_pct:+.2f}% ({move.close:.2f})"


def side_kr(side: str) -> str:
    return "롱" if side == "LONG" else "숏"


def side_icon(side: str) -> str:
    return "🟢" if side == "LONG" else "🔴"


def compact_reasons(reasons: list[str], limit: int = 2) -> str:
    if not reasons:
        return "근거 부족"
    return " / ".join(reasons[:limit])


def compact_market_summary(context: list[MarketMove]) -> str:
    if not context:
        return "확인 불가"

    long_bias, short_bias, notes = score_market_bias(context)
    if long_bias > short_bias + 1:
        direction = "롱 우호"
    elif short_bias > long_bias + 1:
        direction = "숏 우호"
    else:
        direction = "혼조"

    if not notes:
        return direction
    return f"{direction} ({', '.join(notes[:2])})"


def compact_action_for(level: int, side: str | None = None) -> str:
    if level >= 5:
        return "진입 금지"
    if level == 4 and side:
        return f"{side_kr(side)} 강한 후보. 조건 맞으면 검토"
    if level == 3 and side:
        return f"{side_kr(side)} 후보. 확인봉 전까지 대기"
    if level == 2:
        return "대기. 아직 진입 아님"
    return "보기만. 아무것도 안 함"


def section(title: str) -> list[str]:
    return ["", "━━━━━━━━━━━━", title, "━━━━━━━━━━━━"]


def signal_horizon(signal: SignalCandidate) -> str:
    if "라운딩" in signal.setup_type:
        return "1~3시간 확인형"
    if "바닥 횡보" in signal.setup_type:
        return "3~4시간 관찰형"
    return "1~4시간 확인"


def signal_action(signal: SignalCandidate) -> str:
    side = side_kr(signal.side)
    if "라운딩" in signal.setup_type:
        return f"차트 열고 {side} 라운딩 반전 확인"
    if "P라인 바닥 횡보" in signal.setup_type:
        return f"차트 열고 {side} 진입 가능 후보"
    if "바닥 횡보" in signal.setup_type:
        return f"차트 열고 {side} 진입 가능 후보"
    return f"{side} 후보지만 신뢰 낮음. 패스 우선"


def trade_status_title(signal: SignalCandidate) -> str:
    side = side_kr(signal.side).upper()
    if signal.level >= 4:
        return f"{side_icon(signal.side)} {side} 진입 가능 후보"
    return f"{side_icon(signal.side)} {side} 관찰 후보"


def trade_next_step(signal: SignalCandidate) -> str:
    side = side_kr(signal.side)
    if signal.level >= 4:
        return f"지금 할 일: 손절 가능하면 소액 {side}"
    return f"지금 할 일: 차트 확인. 바로 추격 X"


def trade_entry_condition(signal: SignalCandidate) -> str:
    if "라운딩 바닥" in signal.setup_type:
        return "조건: 짧아진 봉 위로 롱 확인봉"
    if "라운딩 천장" in signal.setup_type:
        return "조건: 짧아진 봉 아래로 숏 확인봉"
    if "P라인 바닥 횡보" in signal.setup_type:
        return "조건: P라인 위/근처에서 박스 유지"
    if "바닥 횡보" in signal.setup_type:
        return "조건: 바닥 박스 저점 유지"
    return "조건: 확인봉 방향 유지"


def format_stop_line(signal: SignalCandidate) -> str:
    direction = "아래" if signal.side == "LONG" else "위"
    return f"{signal.stop:.2f} {direction} 5분봉 마감"


def format_signal_message(
    symbol: str,
    signal: SignalCandidate,
    context: list[MarketMove],
    headlines: list[str],
) -> str:
    caution_text = "없음" if not signal.cautions else " / ".join(signal.cautions[:2])
    first_target = signal.entry + 50.0 if signal.side == "LONG" else signal.entry - 50.0
    next_level_text = ""
    if abs(signal.target1 - first_target) > 1.0:
        next_level_text = f"다음 레벨: {signal.target1:.2f}"
    lines = [
        trade_status_title(signal),
        f"{symbol} {signal.entry:.2f}",
        "",
        trade_next_step(signal),
        trade_entry_condition(signal),
        "",
        f"진입: {signal.entry:.2f}",
        f"무효: {format_stop_line(signal)}",
        f"1차 목표: {first_target:.2f} (+50pt)",
        *([next_level_text] if next_level_text else []),
        "",
        f"유형: {signal.setup_type.replace(' 확인', '')}",
        f"시간: {signal_horizon(signal)}",
        f"근거: {compact_reasons(signal.reasons, 2)}",
        f"주의: {caution_text}",
        "",
        f"{kst_time_string(signal.bar_time)}",
    ]
    return "\n".join(lines)


def format_watch_message(symbol: str, status: WatchStatus, context: list[MarketMove]) -> str:
    lines = [
        "❌ 지금 진입 금지",
        f"{symbol} {status.current_price:.2f}",
        "",
        "지금 할 일: 아무것도 누르지 않기",
        "",
        f"이유: {compact_reasons(status.reasons, 2)}",
        f"주의: {'없음' if not status.cautions else ' / '.join(status.cautions[:2])}",
        "",
        f"{kst_time_string(status.bar_time)}",
    ]
    return "\n".join(lines)


def send_telegram_message(text: str) -> tuple[bool, str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return False, "telegram_not_configured"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    body = json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=15) as response:
            return True, response.read().decode("utf-8", "replace")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        return False, f"http_{exc.code}:{detail}"
    except URLError as exc:
        return False, f"url_error:{exc.reason}"
    except TimeoutError:
        return False, "timeout"


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)


def encode_png(width: int, height: int, pixels: bytearray) -> bytes:
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)
        raw.extend(pixels[y * stride : (y + 1) * stride])
    header = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return header + png_chunk(b"IHDR", ihdr) + png_chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + png_chunk(b"IEND", b"")


def set_pixel(pixels: bytearray, width: int, height: int, x: int, y: int, color: tuple[int, int, int]) -> None:
    if 0 <= x < width and 0 <= y < height:
        index = (y * width + x) * 3
        pixels[index : index + 3] = bytes(color)


def draw_line(
    pixels: bytearray,
    width: int,
    height: int,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    color: tuple[int, int, int],
) -> None:
    dx = abs(x2 - x1)
    dy = -abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx + dy
    x, y = x1, y1
    while True:
        set_pixel(pixels, width, height, x, y, color)
        if x == x2 and y == y2:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def fill_rect(
    pixels: bytearray,
    width: int,
    height: int,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    color: tuple[int, int, int],
) -> None:
    left, right = sorted((max(0, x1), min(width - 1, x2)))
    top, bottom = sorted((max(0, y1), min(height - 1, y2)))
    for y in range(top, bottom + 1):
        for x in range(left, right + 1):
            set_pixel(pixels, width, height, x, y, color)


def make_chart_png(bars: list[Bar], signal: SignalCandidate, pivots: PivotLevels | None) -> bytes:
    width, height = 900, 520
    bg = (18, 23, 34)
    grid = (42, 49, 64)
    green = (0, 186, 124)
    red = (255, 73, 83)
    white = (230, 232, 236)
    yellow = (255, 190, 80)
    blue = (70, 140, 255)

    pixels = bytearray(bg * (width * height))
    left, right, top, bottom = 50, 850, 40, 470
    visible = bars[-80:]
    price_values = [bar.high for bar in visible] + [bar.low for bar in visible] + [signal.entry, signal.stop, signal.target1]
    if pivots:
        price_values.extend([pivots.pp, pivots.r1, pivots.r2, pivots.s1, pivots.s2])
    price_min, price_max = min(price_values), max(price_values)
    pad = max((price_max - price_min) * 0.12, 1.0)
    price_min -= pad
    price_max += pad

    def x_for(index: int) -> int:
        if len(visible) == 1:
            return left
        return int(left + (index / (len(visible) - 1)) * (right - left))

    def y_for(price: float) -> int:
        return int(bottom - ((price - price_min) / (price_max - price_min)) * (bottom - top))

    for i in range(6):
        y = int(top + i * (bottom - top) / 5)
        draw_line(pixels, width, height, left, y, right, y, grid)
    for i in range(9):
        x = int(left + i * (right - left) / 8)
        draw_line(pixels, width, height, x, top, x, bottom, grid)

    for idx, bar in enumerate(visible):
        x = x_for(idx)
        color = green if bar.close >= bar.open else red
        draw_line(pixels, width, height, x, y_for(bar.high), x, y_for(bar.low), color)
        body_top = y_for(max(bar.open, bar.close))
        body_bottom = y_for(min(bar.open, bar.close))
        fill_rect(pixels, width, height, x - 3, body_top, x + 3, max(body_bottom, body_top + 1), color)

    level_lines: list[tuple[float, tuple[int, int, int]]] = [(signal.entry, blue), (signal.stop, red), (signal.target1, green)]
    if pivots:
        level_lines.extend((level, yellow) for level in [pivots.pp, pivots.r1, pivots.s1])
    for level, color in level_lines:
        y = y_for(level)
        draw_line(pixels, width, height, left, y, right, y, color)

    return encode_png(width, height, pixels)


def send_telegram_photo(caption: str, image_bytes: bytes) -> tuple[bool, str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return False, "telegram_not_configured"

    boundary = f"----codex-{uuid4().hex}"
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    parts: list[bytes] = []
    fields = {"chat_id": chat_id, "caption": caption}
    for name, value in fields.items():
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        parts.append(str(value).encode("utf-8"))
        parts.append(b"\r\n")
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(b'Content-Disposition: form-data; name="photo"; filename="us100_signal.png"\r\n')
    parts.append(b"Content-Type: image/png\r\n\r\n")
    parts.append(image_bytes)
    parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)
    request = Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=25) as response:
            return True, response.read().decode("utf-8", "replace")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        return False, f"http_{exc.code}:{detail}"
    except URLError as exc:
        return False, f"url_error:{exc.reason}"
    except TimeoutError:
        return False, "timeout"


def run_once(
    symbol: str,
    interval: str,
    range_name: str,
    min_level: int,
    min_rr: float,
    dry_run: bool,
    chart: bool,
    quiet_no_signal: bool = False,
) -> int:
    bars = parse_bars(fetch_chart(symbol, interval, range_name))
    if len(bars) < 80:
        print(f"Not enough bars for {symbol}.")
        return 0

    pivots = compute_pivots(symbol)
    context = fetch_context_snapshot()
    signal = analyze_signal(bars, pivots, context, min_rr)
    if signal is None or signal.level < min_level:
        if not quiet_no_signal:
            status = build_watch_status(bars, pivots, context)
            print(format_watch_message(symbol, status, context))
        return 0

    state = load_state()
    dedupe_key = f"{symbol}:{signal.bar_time}:L{signal.level}:{signal.side}:{signal.setup_type}:{round(signal.entry, 1)}"
    if state.get("last_signal_key") == dedupe_key:
        if not quiet_no_signal:
            print("Duplicate signal already sent.")
        return 0

    headlines = fetch_relevant_headlines()
    text = format_signal_message(symbol, signal, context, headlines)

    ok = True
    detail = "dry_run"
    if dry_run:
        print(text)
    elif chart:
        image_bytes = make_chart_png(bars, signal, pivots)
        ok, detail = send_telegram_photo(text[:1024], image_bytes)
        if ok and len(text) > 1024:
            ok, detail = send_telegram_message(text)
    else:
        ok, detail = send_telegram_message(text)

    record = {
        "sent_at": datetime.now(tz=timezone.utc).isoformat(),
        "symbol": symbol,
        "side": signal.side,
        "setup_type": signal.setup_type,
        "level": signal.level,
        "level_name": signal.level_name,
        "decision": signal.decision,
        "score": signal.score,
        "entry": signal.entry,
        "stop": signal.stop,
        "target1": signal.target1,
        "target2": signal.target2,
        "rr": signal.rr,
        "bar_time": signal.bar_time,
        "reasons": signal.reasons,
        "cautions": signal.cautions,
        "headlines": headlines,
        "telegram_ok": ok,
        "telegram_detail": detail if ok else detail[:500],
        "dry_run": dry_run,
    }
    append_log(record)

    if not ok:
        print(f"Telegram send failed: {detail}")
        return 1

    state["last_signal_key"] = dedupe_key
    save_state(state)
    print("Signal alert sent." if not dry_run else "Dry-run signal printed.")
    return 0


def run_loop(
    symbol: str,
    interval: str,
    range_name: str,
    min_level: int,
    min_rr: float,
    poll_seconds: int,
    heartbeat_minutes: int,
    dry_run: bool,
    chart: bool,
) -> int:
    print(
        f"Starting signal loop. symbol={symbol} interval={interval} "
        f"level>={min_level} min_rr={min_rr:.2f} poll={poll_seconds}s"
    )
    checks_since_heartbeat = 0
    heartbeat_every_checks = max(1, int((heartbeat_minutes * 60) / poll_seconds))
    while True:
        try:
            run_once(symbol, interval, range_name, min_level, min_rr, dry_run, chart, quiet_no_signal=True)
            checks_since_heartbeat += 1
            if checks_since_heartbeat >= heartbeat_every_checks:
                now_kst = datetime.now(tz=timezone.utc).astimezone(KST).strftime("%Y-%m-%d %H:%M:%S KST")
                print(f"Waiting... no LEVEL {min_level}+ signal yet for {symbol} ({now_kst})")
                checks_since_heartbeat = 0
        except Exception as exc:  # noqa: BLE001
            append_log({"sent_at": datetime.now(tz=timezone.utc).isoformat(), "type": "error", "message": str(exc)})
            print(f"Loop error: {exc}", file=sys.stderr)
        time.sleep(poll_seconds)


def parse_args(argv: list[str]) -> dict[str, Any]:
    config: dict[str, Any] = {
        "once": "--once" in argv,
        "dry_run": "--dry-run" in argv,
        "chart": "--no-chart" not in argv,
        "symbol": DEFAULT_SYMBOL,
        "interval": DEFAULT_INTERVAL,
        "range_name": DEFAULT_RANGE,
        "min_level": DEFAULT_MIN_LEVEL,
        "min_rr": DEFAULT_MIN_RR,
        "poll_seconds": DEFAULT_POLL_SECONDS,
        "heartbeat_minutes": DEFAULT_HEARTBEAT_MINUTES,
    }
    for arg in argv:
        if arg.startswith("--symbol="):
            config["symbol"] = arg.split("=", 1)[1]
        elif arg.startswith("--interval="):
            config["interval"] = arg.split("=", 1)[1]
        elif arg.startswith("--range="):
            config["range_name"] = arg.split("=", 1)[1]
        elif arg.startswith("--min-level="):
            config["min_level"] = int(arg.split("=", 1)[1])
        elif arg.startswith("--score-threshold="):
            # Backward compatibility with the older score wording.
            config["min_level"] = 4 if int(arg.split("=", 1)[1]) >= 8 else 3
        elif arg.startswith("--min-rr="):
            config["min_rr"] = float(arg.split("=", 1)[1])
        elif arg.startswith("--poll="):
            config["poll_seconds"] = int(arg.split("=", 1)[1])
        elif arg.startswith("--heartbeat-minutes="):
            config["heartbeat_minutes"] = int(arg.split("=", 1)[1])
    return config


def main(argv: list[str]) -> int:
    load_env_file(AUTOTRADE_ENV)
    config = parse_args(argv)
    if not config["dry_run"] and (
        not os.environ.get("TELEGRAM_BOT_TOKEN") or not os.environ.get("TELEGRAM_CHAT_ID")
    ):
        print("Telegram env is missing. Check autotrade_mvp/.env first.", file=sys.stderr)
        return 1

    if config["once"]:
        return run_once(
            config["symbol"],
            config["interval"],
            config["range_name"],
            config["min_level"],
            config["min_rr"],
            config["dry_run"],
            config["chart"],
        )
    return run_loop(
        config["symbol"],
        config["interval"],
        config["range_name"],
        config["min_level"],
        config["min_rr"],
        config["poll_seconds"],
        config["heartbeat_minutes"],
        config["dry_run"],
        config["chart"],
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
