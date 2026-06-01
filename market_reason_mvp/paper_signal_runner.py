#!/usr/bin/env python3
"""
Forward paper trader for the US100/NQ signal bot.

This does not send Telegram messages and does not place real trades. It records
what would have happened if a beginner followed the allowed signal cards.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import market_signal_bot as bot


LOG_DIR = bot.PROJECT_DIR / "logs"
STATE_PATH = LOG_DIR / "paper_signal_state.json"
JSONL_PATH = LOG_DIR / "paper_trades.jsonl"
CSV_PATH = LOG_DIR / "paper_trades.csv"


def now_kst() -> datetime:
    return datetime.now(bot.KST)


def default_until() -> datetime:
    now = now_kst()
    target = now.replace(hour=2, minute=0, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    return target


def parse_until(value: str) -> datetime:
    if not value:
        return default_until()
    parsed = datetime.strptime(value, "%Y-%m-%d %H:%M")
    return parsed.replace(tzinfo=bot.KST)


def should_stop(once: bool, continuous: bool, until_dt: datetime) -> bool:
    if once:
        return True
    if continuous:
        return False
    return now_kst() >= until_dt


def text_time(unix_ts: int) -> str:
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc).astimezone(bot.KST).strftime("%Y-%m-%d %H:%M:%S KST")


def load_state(reset: bool, until_text: str) -> dict[str, Any]:
    if reset and STATE_PATH.exists():
        STATE_PATH.unlink()
    if reset:
        for path in (JSONL_PATH, CSV_PATH):
            if path.exists():
                path.unlink()
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {
        "session_started_at": now_kst().isoformat(),
        "until": until_text,
        "open_trade": None,
        "closed_trades": [],
        "seen_signal_keys": [],
    }


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def append_jsonl(record: dict[str, Any]) -> None:
    with JSONL_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def append_csv(record: dict[str, Any]) -> None:
    fields = [
        "event",
        "result",
        "symbol",
        "side",
        "setup_type",
        "level",
        "entry",
        "stop",
        "target",
        "exit_price",
        "pnl_points",
        "opened_at",
        "closed_at",
        "reason",
    ]
    exists = CSV_PATH.exists()
    with CSV_PATH.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow({field: record.get(field, "") for field in fields})


def append_event(record: dict[str, Any]) -> None:
    append_jsonl(record)
    append_csv(record)


def signal_key(symbol: str, signal: bot.SignalCandidate) -> str:
    return f"{symbol}:{signal.bar_time}:{signal.side}:{signal.setup_type}:{round(signal.entry, 1)}"


def fixed_target(signal: bot.SignalCandidate, profit_points: float) -> float:
    if signal.side == "LONG":
        return signal.entry + profit_points
    return signal.entry - profit_points


def detect_signal(
    symbol: str,
    interval: str,
    range_name: str,
    min_level: int,
    min_rr: float,
    setup_contains: str,
) -> tuple[bot.SignalCandidate | None, list[bot.Bar]]:
    bars = bot.parse_bars(bot.fetch_chart(symbol, interval, range_name))
    pivots = bot.compute_pivots(symbol)
    try:
        context = bot.fetch_context_snapshot()
    except Exception:
        context = []
    signal = bot.analyze_signal(bars, pivots, context, min_rr)
    if signal is None or signal.level < min_level:
        return None, bars
    if setup_contains and not setup_matches(signal.setup_type, setup_contains):
        return None, bars
    return signal, bars


def setup_matches(setup_type: str, setup_contains: str) -> bool:
    tokens = [token.strip() for token in setup_contains.replace("|", ",").split(",") if token.strip()]
    if not tokens:
        return True
    return any(token in setup_type for token in tokens)


def open_trade(
    state: dict[str, Any],
    symbol: str,
    signal: bot.SignalCandidate,
    profit_points: float,
) -> None:
    target = fixed_target(signal, profit_points)
    trade = {
        "symbol": symbol,
        "side": signal.side,
        "setup_type": signal.setup_type,
        "level": signal.level,
        "entry": signal.entry,
        "stop": signal.stop,
        "target": target,
        "opened_at": signal.bar_time,
        "opened_at_text": text_time(signal.bar_time),
        "signal_key": signal_key(symbol, signal),
        "reason": " / ".join(signal.reasons[:2]),
    }
    state["open_trade"] = trade
    state["seen_signal_keys"] = [*state.get("seen_signal_keys", []), trade["signal_key"]][-200:]
    append_event(
        {
            "event": "OPEN",
            "symbol": symbol,
            "side": trade["side"],
            "setup_type": trade["setup_type"],
            "level": trade["level"],
            "entry": trade["entry"],
            "stop": trade["stop"],
            "target": trade["target"],
            "opened_at": trade["opened_at_text"],
            "reason": trade["reason"],
        }
    )
    print(f"OPEN {trade['side']} {trade['setup_type']} entry={trade['entry']:.2f} target={trade['target']:.2f}")


def close_trade(
    state: dict[str, Any],
    trade: dict[str, Any],
    result: str,
    exit_price: float,
    closed_at: int,
    reason: str,
) -> None:
    if trade["side"] == "LONG":
        pnl = exit_price - trade["entry"]
    else:
        pnl = trade["entry"] - exit_price
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
    append_event(
        {
            "event": "CLOSE",
            "result": result,
            "symbol": trade["symbol"],
            "side": trade["side"],
            "setup_type": trade["setup_type"],
            "level": trade["level"],
            "entry": trade["entry"],
            "stop": trade["stop"],
            "target": trade["target"],
            "exit_price": exit_price,
            "pnl_points": pnl,
            "opened_at": trade["opened_at_text"],
            "closed_at": closed["closed_at_text"],
            "reason": reason,
        }
    )
    print(f"CLOSE {result} pnl={pnl:+.2f}pt reason={reason}")


def summary_numbers(state: dict[str, Any]) -> tuple[int, int, int, float, float]:
    trades = state.get("closed_trades", [])
    total = len(trades)
    wins = sum(1 for trade in trades if trade.get("result") == "WIN")
    losses = sum(1 for trade in trades if trade.get("result") == "LOSS")
    pnl = sum(float(trade.get("pnl_points", 0.0)) for trade in trades)
    avg = pnl / total if total else 0.0
    return total, wins, losses, pnl, avg


def update_open_trade(state: dict[str, Any], bars: list[bot.Bar]) -> None:
    trade = state.get("open_trade")
    if not trade:
        return
    future = [bar for bar in bars if bar.ts > trade["opened_at"]]
    for bar in future:
        if trade["side"] == "LONG":
            if bar.high >= trade["target"]:
                close_trade(state, trade, "WIN", trade["target"], bar.ts, "+50pt target hit")
                return
            if bar.close < trade["stop"]:
                close_trade(state, trade, "LOSS", bar.close, bar.ts, "5m close below invalidation")
                return
        else:
            if bar.low <= trade["target"]:
                close_trade(state, trade, "WIN", trade["target"], bar.ts, "+50pt target hit")
                return
            if bar.close > trade["stop"]:
                close_trade(state, trade, "LOSS", bar.close, bar.ts, "5m close above invalidation")
                return


def force_close_if_needed(state: dict[str, Any], bars: list[bot.Bar]) -> None:
    trade = state.get("open_trade")
    if not trade or not bars:
        return
    last = bars[-1]
    result = "WIN" if (last.close - trade["entry"] if trade["side"] == "LONG" else trade["entry"] - last.close) > 0 else "LOSS"
    close_trade(state, trade, result, last.close, last.ts, "forced close at session end")


def print_summary(state: dict[str, Any]) -> None:
    total, wins, losses, pnl, avg = summary_numbers(state)
    print()
    print("[초보자 페이퍼 결과]")
    print(f"매매 횟수: {total}")
    print(f"승/패: {wins}승 {losses}패")
    print(f"총 포인트: {pnl:+.2f}pt")
    print(f"매매당 평균: {avg:+.2f}pt")
    if state.get("open_trade"):
        trade = state["open_trade"]
        print(f"열린 포지션: {trade['side']} entry={trade['entry']:.2f}")


def format_trade_rows(state: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    for index, trade in enumerate(state.get("closed_trades", []), start=1):
        rows.append(
            f"{index}. {trade['side']} {trade['result']} "
            f"{float(trade['pnl_points']):+.1f}pt "
            f"({trade['opened_at_text']} -> {trade['closed_at_text']})"
        )
    return rows


def final_report_text(
    state: dict[str, Any],
    symbol: str,
    min_level: int,
    setup_contains: str,
    profit_points: float,
) -> str:
    total, wins, losses, pnl, avg = summary_numbers(state)
    started_at = state.get("session_started_at", "")
    until_text = state.get("until", "")
    setup_name = setup_contains or "전체"
    decision = "유지 후보" if total > 0 and pnl > 0 else "조건이 엄격함. 더 완화할지 검토"
    if total >= 3 and wins / total >= 0.7 and pnl > 0:
        decision = "유지 후보. 샘플을 더 모으기"
    elif total >= 3 and pnl <= 0:
        decision = "폐기 또는 조건 강화 필요"

    lines = [
        "📊 초보자 모의매매 리포트",
        "",
        f"기간: {started_at} ~ {until_text}",
        f"전략: {symbol} / 5분봉 / LEVEL {min_level}+ / {setup_name} / +{profit_points:.0f}pt",
        "",
        "결과:",
        f"매매 횟수: {total}회",
        f"승패: {wins}승 {losses}패",
        f"총 포인트: {pnl:+.2f}pt",
        f"매매당 평균: {avg:+.2f}pt",
        "",
        "매매 내역:",
    ]
    rows = format_trade_rows(state)
    lines.extend(rows if rows else ["없음"])
    lines.extend(
        [
            "",
            "판단:",
            "신호가 없으면 실패가 아니라 조건이 엄격했던 것이다." if total == 0 else decision,
            "",
            "다음 결정:",
            decision,
        ]
    )
    return "\n".join(lines)


def send_telegram_if_requested(text: str, enabled: bool) -> None:
    if not enabled:
        return
    ok, detail = bot.send_telegram_message(text)
    if ok:
        print("Telegram report sent.")
    else:
        print(f"Telegram report failed: {detail}")


def tick(
    state: dict[str, Any],
    symbol: str,
    interval: str,
    range_name: str,
    min_level: int,
    min_rr: float,
    setup_contains: str,
    profit_points: float,
) -> None:
    signal, bars = detect_signal(symbol, interval, range_name, min_level, min_rr, setup_contains)
    update_open_trade(state, bars)
    if state.get("open_trade"):
        print(f"보유 중. {now_kst().strftime('%Y-%m-%d %H:%M:%S KST')}")
        return
    if signal is None:
        print(f"대기. 신호 없음. {now_kst().strftime('%Y-%m-%d %H:%M:%S KST')}")
        return
    key = signal_key(symbol, signal)
    if key in state.get("seen_signal_keys", []):
        print(f"대기. 이미 기록한 신호. {now_kst().strftime('%Y-%m-%d %H:%M:%S KST')}")
        return
    open_trade(state, symbol, signal, profit_points)


def main() -> int:
    bot.load_env_file(bot.AUTOTRADE_ENV)
    parser = argparse.ArgumentParser(description="Forward paper-trade beginner signal cards.")
    parser.add_argument("--symbol", default=bot.DEFAULT_SYMBOL)
    parser.add_argument("--interval", default=bot.DEFAULT_INTERVAL)
    parser.add_argument("--range", default=bot.DEFAULT_RANGE, dest="range_name")
    parser.add_argument("--until", default="")
    parser.add_argument("--poll", type=int, default=60)
    parser.add_argument("--min-level", type=int, default=2)
    parser.add_argument("--min-rr", type=float, default=bot.DEFAULT_MIN_RR)
    parser.add_argument("--setup-contains", default="라운딩,P라인")
    parser.add_argument("--profit-points", type=float, default=50.0)
    parser.add_argument("--send-telegram-start", action="store_true")
    parser.add_argument("--send-telegram-final", action="store_true")
    parser.add_argument("--idle-after-finish", action="store_true")
    parser.add_argument("--continuous", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    until_dt = parse_until(args.until)
    until_text = "continuous" if args.continuous else until_dt.isoformat()
    state = load_state(args.reset, until_text)
    mode_text = "계속 감시" if args.continuous else until_dt.strftime("%Y-%m-%d %H:%M KST")
    print(
        "초보자 페이퍼 시작 "
        f"symbol={args.symbol} min_level={args.min_level} setup={args.setup_contains or 'ALL'} "
        f"until={mode_text}"
    )
    if args.send_telegram_start and not state.get("start_report_sent"):
        start_text = (
            "🧪 초보자 모의매매 테스트 시작\n\n"
            f"전략: {args.symbol} / 5분봉 / LEVEL {args.min_level}+ / {args.setup_contains or '전체'}\n"
            f"목표: +{args.profit_points:.0f}pt\n"
            f"종료: {mode_text}\n\n"
            "실제 주문 아님. 결과 확인용."
        )
        send_telegram_if_requested(start_text, True)
        state["start_report_sent"] = True
        save_state(state)

    last_bars: list[bot.Bar] = []
    try:
        while True:
            signal, bars = detect_signal(
                args.symbol,
                args.interval,
                args.range_name,
                args.min_level,
                args.min_rr,
                args.setup_contains,
            )
            last_bars = bars
            update_open_trade(state, bars)
            if not state.get("open_trade") and signal is not None:
                key = signal_key(args.symbol, signal)
                if key not in state.get("seen_signal_keys", []):
                    open_trade(state, args.symbol, signal, args.profit_points)
                else:
                    print(f"대기. 이미 기록한 신호. {now_kst().strftime('%Y-%m-%d %H:%M:%S KST')}")
            elif state.get("open_trade"):
                print(f"보유 중. {now_kst().strftime('%Y-%m-%d %H:%M:%S KST')}")
            else:
                print(f"대기. 신호 없음. {now_kst().strftime('%Y-%m-%d %H:%M:%S KST')}")
            save_state(state)
            if should_stop(args.once, args.continuous, until_dt):
                break
            time.sleep(max(5, args.poll))
    except KeyboardInterrupt:
        print("\n사용자 중지.")

    if not args.continuous and now_kst() >= until_dt:
        force_close_if_needed(state, last_bars)
        if not state.get("final_report_sent"):
            report = final_report_text(state, args.symbol, args.min_level, args.setup_contains, args.profit_points)
            print()
            print(report)
            send_telegram_if_requested(report, args.send_telegram_final)
            state["final_report_sent"] = True
        save_state(state)
    print_summary(state)
    if not args.continuous and now_kst() >= until_dt and args.idle_after_finish:
        print("테스트 종료. Render 삭제 전까지 대기 상태로 유지합니다.")
        while True:
            time.sleep(3600)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
