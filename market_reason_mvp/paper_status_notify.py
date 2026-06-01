#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import market_signal_bot as bot


ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT / "logs" / "paper_signal_state.json"
LOG_PATH = ROOT / "logs" / "paper_runner_live.log"
KST = ZoneInfo("Asia/Seoul")


def runner_alive() -> bool:
    try:
        output = subprocess.check_output(["pgrep", "-af", "paper_signal_runner.py"], text=True)
    except subprocess.CalledProcessError:
        return False
    return bool(output.strip())


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"error": str(exc)}


def last_log_line() -> str:
    if not LOG_PATH.exists():
        return "로그 없음"
    lines = [line for line in LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
    return lines[-1] if lines else "로그 없음"


def summary_numbers(state: dict) -> tuple[int, int, int, float, float]:
    trades = state.get("closed_trades", [])
    total = len(trades)
    wins = sum(1 for trade in trades if trade.get("result") == "WIN")
    losses = sum(1 for trade in trades if trade.get("result") == "LOSS")
    pnl = sum(float(trade.get("pnl_points", 0.0)) for trade in trades)
    avg = pnl / total if total else 0.0
    return total, wins, losses, pnl, avg


def build_status_text() -> str:
    state = load_state()
    total, wins, losses, pnl, avg = summary_numbers(state)
    alive_text = "감시 중" if runner_alive() else "꺼짐"
    open_trade = state.get("open_trade")
    if open_trade:
        position = (
            f"{open_trade.get('side')} entry={float(open_trade.get('entry', 0)):.2f} "
            f"target={float(open_trade.get('target', 0)):.2f} stop={float(open_trade.get('stop', 0)):.2f}"
        )
    else:
        position = "없음"

    return "\n".join(
        [
            "[쭈꾸미 상태 알림]",
            "",
            f"상태: {alive_text}",
            "전략: NQ=F / 5분봉 / 라운딩+P라인 / LEVEL 2+ / +50pt",
            f"기간: {state.get('session_started_at', '없음')} ~ {state.get('until', '없음')}",
            "",
            f"열린 포지션: {position}",
            f"매매 횟수: {total}회",
            f"승패: {wins}승 {losses}패",
            f"총 포인트: {pnl:+.2f}pt",
            f"평균 포인트: {avg:+.2f}pt",
            "",
            f"최근 로그: {last_log_line()}",
            f"확인 시각: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S KST')}",
        ]
    )


def main() -> int:
    bot.load_env_file(bot.AUTOTRADE_ENV)
    text = build_status_text()
    ok, detail = bot.send_telegram_message(text)
    if ok:
        print("telegram_status_sent")
        return 0
    print(f"telegram_status_failed: {detail}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
