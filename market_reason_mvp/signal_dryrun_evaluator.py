#!/usr/bin/env python3
"""
Dry-run evaluator for US100 signal quality.

This script does not send Telegram messages. It replays recent 5-minute bars,
finds historical signals with the current chart-first logic, and scores whether
a fixed profit target was reached before invalidation.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import market_signal_bot as bot


ET = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class EvaluatedSignal:
    index: int
    time_text: str
    side: str
    setup_type: str
    level: int
    entry: float
    stop: float
    target: float
    rr: float
    result: str
    reason: str


def trading_date_et(unix_ts: int) -> datetime.date:
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc).astimezone(ET).date()


def pivot_for_time(unix_ts: int, daily_bars: list[bot.Bar]) -> bot.PivotLevels | None:
    current_date = trading_date_et(unix_ts)
    previous_days = [bar for bar in daily_bars if trading_date_et(bar.ts) < current_date]
    if not previous_days:
        return None

    prev = previous_days[-1]
    pp = (prev.high + prev.low + prev.close) / 3.0
    return bot.PivotLevels(
        pp=pp,
        r1=2.0 * pp - prev.low,
        r2=pp + (prev.high - prev.low),
        s1=2.0 * pp - prev.high,
        s2=pp - (prev.high - prev.low),
    )


def evaluate_future(
    signal: bot.SignalCandidate,
    future_bars: list[bot.Bar],
    profit_points: float,
) -> tuple[str, str, float]:
    target = signal.target1
    if profit_points > 0:
        target = signal.entry + profit_points if signal.side == "LONG" else signal.entry - profit_points

    if signal.side == "LONG":
        for bar in future_bars:
            if bar.high >= target:
                return "WIN", f"+{profit_points:.1f}pt hit before invalidation", target
            if bar.close < signal.stop:
                return "LOSS", f"5m close invalidated before +{profit_points:.1f}pt", target
        return "MISS", f"neither +{profit_points:.1f}pt nor invalidation within lookahead", target

    for bar in future_bars:
        if bar.low <= target:
            return "WIN", f"+{profit_points:.1f}pt hit before invalidation", target
        if bar.close > signal.stop:
            return "LOSS", f"5m close invalidated before +{profit_points:.1f}pt", target
    return "MISS", f"neither +{profit_points:.1f}pt nor invalidation within lookahead", target


def collect_evaluations(
    symbol: str,
    interval: str,
    range_name: str,
    sample_size: int,
    min_level: int,
    min_rr: float,
    lookahead_bars: int,
    signal_gap_bars: int,
    profit_points: float,
    setup_contains: str = "",
    date_kst: str = "",
) -> list[EvaluatedSignal]:
    bars = bot.parse_bars(bot.fetch_chart(symbol, interval, range_name))
    daily_bars = bot.parse_bars(bot.fetch_chart(symbol, "1d", "6mo"))

    evaluations: list[EvaluatedSignal] = []
    last_signal_index = -10_000
    last_key = ""

    for index in range(85, len(bars) - lookahead_bars):
        if index - last_signal_index <= signal_gap_bars:
            continue

        window = bars[: index + 1]
        pivots = pivot_for_time(window[-1].ts, daily_bars)

        # Historical context/news are intentionally excluded here. The rebuild
        # target is chart-first accuracy; macro/news should later downgrade risk.
        signal = bot.analyze_signal(window, pivots, [], min_rr)
        if signal is None or signal.level < min_level:
            continue
        if setup_contains and setup_contains not in signal.setup_type:
            continue
        if date_kst:
            signal_date = datetime.fromtimestamp(signal.bar_time, tz=timezone.utc).astimezone(bot.KST).date().isoformat()
            if signal_date != date_kst:
                continue

        key = f"{signal.side}:{signal.setup_type}:{round(signal.entry, 1)}"
        if key == last_key:
            continue

        future = bars[index + 1 : index + 1 + lookahead_bars]
        result, reason, target = evaluate_future(signal, future, profit_points)
        evaluations.append(
            EvaluatedSignal(
                index=index,
                time_text=bot.kst_time_string(signal.bar_time),
                side=signal.side,
                setup_type=signal.setup_type,
                level=signal.level,
                entry=signal.entry,
                stop=signal.stop,
                target=target,
                rr=signal.rr,
                result=result,
                reason=reason,
            )
        )
        last_signal_index = index
        last_key = key

    return evaluations[-sample_size:]


def default_required_wins(sample_size: int) -> int:
    if sample_size == 10:
        return 8
    if sample_size == 20:
        return 12
    return max(1, (sample_size * 8 + 9) // 10)


def print_report(evaluations: list[EvaluatedSignal], sample_size: int, required_wins: int) -> int:
    if not evaluations:
        print("No historical signals found for this configuration.")
        return 1

    wins = sum(1 for item in evaluations if item.result == "WIN")
    losses = sum(1 for item in evaluations if item.result == "LOSS")
    misses = sum(1 for item in evaluations if item.result == "MISS")

    print(f"[DRY-RUN EVALUATION] last {len(evaluations)} signals")
    print(f"WIN={wins} LOSS={losses} MISS={misses}")
    print(f"PASS 기준: {sample_size}개 중 {required_wins}개 이상 WIN")
    if len(evaluations) >= sample_size and wins >= required_wins:
        print("RESULT: PASS")
    else:
        print("RESULT: FAIL / keep Telegram sending paused")
    print()

    for number, item in enumerate(evaluations, start=1):
        print(
            f"{number:02d}. {item.time_text} {item.side} L{item.level} "
            f"{item.result} entry={item.entry:.2f} stop={item.stop:.2f} "
            f"target={item.target:.2f} rr={item.rr:.2f} "
            f"setup={item.setup_type} ({item.reason})"
        )

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate dry-run signal accuracy without Telegram.")
    parser.add_argument("--symbol", default=bot.DEFAULT_SYMBOL)
    parser.add_argument("--interval", default=bot.DEFAULT_INTERVAL)
    parser.add_argument("--range", default="60d", dest="range_name")
    parser.add_argument("--sample", type=int, default=10)
    parser.add_argument("--min-level", type=int, default=bot.DEFAULT_MIN_LEVEL)
    parser.add_argument("--min-rr", type=float, default=bot.DEFAULT_MIN_RR)
    parser.add_argument("--profit-points", type=float, default=50.0)
    parser.add_argument("--required-wins", type=int, default=0)
    parser.add_argument("--lookahead-bars", type=int, default=12)
    parser.add_argument("--signal-gap-bars", type=int, default=6)
    parser.add_argument("--setup-contains", default="")
    parser.add_argument("--date-kst", default="")
    args = parser.parse_args()

    evaluations = collect_evaluations(
        symbol=args.symbol,
        interval=args.interval,
        range_name=args.range_name,
        sample_size=args.sample,
        min_level=args.min_level,
        min_rr=args.min_rr,
        lookahead_bars=args.lookahead_bars,
        signal_gap_bars=args.signal_gap_bars,
        profit_points=args.profit_points,
        setup_contains=args.setup_contains,
        date_kst=args.date_kst,
    )
    required_wins = args.required_wins if args.required_wins > 0 else default_required_wins(args.sample)
    return print_report(evaluations, args.sample, required_wins)


if __name__ == "__main__":
    raise SystemExit(main())
