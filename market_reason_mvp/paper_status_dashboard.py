#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "logs"
STATE_PATH = LOG_DIR / "paper_signal_state.json"
LOG_PATH = LOG_DIR / "paper_runner_live.log"
KST = ZoneInfo("Asia/Seoul")


def read_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"error": str(exc)}


def recent_log_lines(limit: int = 28) -> list[str]:
    if not LOG_PATH.exists():
        return []
    lines = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-limit:]


def runner_alive() -> bool:
    try:
        output = subprocess.check_output(["pgrep", "-af", "paper_signal_runner.py"], text=True)
    except subprocess.CalledProcessError:
        return False
    return bool(output.strip())


def summary(state: dict) -> tuple[int, int, int, float, float]:
    trades = state.get("closed_trades", [])
    total = len(trades)
    wins = sum(1 for trade in trades if trade.get("result") == "WIN")
    losses = sum(1 for trade in trades if trade.get("result") == "LOSS")
    pnl = sum(float(trade.get("pnl_points", 0.0)) for trade in trades)
    avg = pnl / total if total else 0.0
    return total, wins, losses, pnl, avg


def esc(value: object) -> str:
    text = str(value)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_html() -> bytes:
    state = read_state()
    alive = runner_alive()
    total, wins, losses, pnl, avg = summary(state)
    open_trade = state.get("open_trade")
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")
    started = state.get("session_started_at", "없음")
    until = state.get("until", "없음")
    status_text = "감시 중" if alive else "꺼짐"
    status_class = "ok" if alive else "bad"
    pnl_class = "ok" if pnl > 0 else "bad" if pnl < 0 else "flat"

    if open_trade:
        position = (
            f"{esc(open_trade.get('side'))} / entry {float(open_trade.get('entry', 0)):.2f} / "
            f"target {float(open_trade.get('target', 0)):.2f} / stop {float(open_trade.get('stop', 0)):.2f}"
        )
    else:
        position = "없음"

    log_html = "\n".join(f"<li>{esc(line)}</li>" for line in recent_log_lines())
    trades_html = "\n".join(
        "<tr>"
        f"<td>{index}</td>"
        f"<td>{esc(trade.get('side', ''))}</td>"
        f"<td>{esc(trade.get('result', ''))}</td>"
        f"<td>{float(trade.get('pnl_points', 0.0)):+.2f}</td>"
        f"<td>{esc(trade.get('opened_at_text', ''))}</td>"
        f"<td>{esc(trade.get('closed_at_text', ''))}</td>"
        "</tr>"
        for index, trade in enumerate(state.get("closed_trades", []), start=1)
    )
    if not trades_html:
        trades_html = '<tr><td colspan="6">아직 청산된 모의매매 없음</td></tr>'

    html = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="15">
  <title>쭈꾸미 모의매매 상태판</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17202a;
      --muted: #667085;
      --line: #d9dee7;
      --panel: #ffffff;
      --bg: #f4f6f8;
      --ok: #16794c;
      --bad: #bf2f2f;
      --flat: #5b6472;
      --accent: #1f5eff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--bg);
    }}
    header {{
      padding: 22px 28px 16px;
      border-bottom: 1px solid var(--line);
      background: #fff;
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 18px;
    }}
    h1 {{ margin: 0; font-size: 24px; letter-spacing: 0; }}
    .sub {{ color: var(--muted); margin-top: 5px; font-size: 14px; }}
    .pill {{
      padding: 9px 13px;
      border-radius: 6px;
      color: #fff;
      font-weight: 700;
      min-width: 92px;
      text-align: center;
    }}
    .ok {{ background: var(--ok); }}
    .bad {{ background: var(--bad); }}
    .flat {{ background: var(--flat); }}
    main {{ padding: 22px 28px 30px; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(150px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 15px;
      min-height: 92px;
    }}
    .label {{ color: var(--muted); font-size: 13px; margin-bottom: 8px; }}
    .value {{ font-size: 22px; font-weight: 750; line-height: 1.2; }}
    .wide {{ grid-column: span 2; }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      margin-top: 16px;
      overflow: hidden;
    }}
    h2 {{
      margin: 0;
      padding: 14px 16px;
      font-size: 17px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfd;
    }}
    ul {{
      margin: 0;
      padding: 12px 18px 14px 32px;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 13px;
      line-height: 1.7;
      max-height: 430px;
      overflow: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
    }}
    th {{ color: var(--muted); background: #fbfcfd; font-weight: 650; }}
    @media (max-width: 900px) {{
      header {{ align-items: start; flex-direction: column; }}
      .grid {{ grid-template-columns: 1fr 1fr; }}
      .wide {{ grid-column: span 2; }}
    }}
    @media (max-width: 560px) {{
      main, header {{ padding-left: 16px; padding-right: 16px; }}
      .grid {{ grid-template-columns: 1fr; }}
      .wide {{ grid-column: span 1; }}
    }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>쭈꾸미 모의매매 상태판</h1>
      <div class="sub">15초마다 자동 새로고침 / 마지막 확인 {esc(now)}</div>
    </div>
    <div class="pill {status_class}">{status_text}</div>
  </header>
  <main>
    <div class="grid">
      <div class="card"><div class="label">전략</div><div class="value">라운딩/P라인 L2+</div></div>
      <div class="card"><div class="label">매매 횟수</div><div class="value">{total}회</div></div>
      <div class="card"><div class="label">승 / 패</div><div class="value">{wins} / {losses}</div></div>
      <div class="card"><div class="label">총 포인트</div><div class="value {pnl_class}">{pnl:+.2f}pt</div></div>
      <div class="card"><div class="label">평균 포인트</div><div class="value">{avg:+.2f}pt</div></div>
      <div class="card"><div class="label">열린 포지션</div><div class="value">{position}</div></div>
      <div class="card wide"><div class="label">검증 시간</div><div class="value">{esc(started)} → {esc(until)}</div></div>
    </div>
    <section>
      <h2>최근 로그</h2>
      <ul>{log_html}</ul>
    </section>
    <section>
      <h2>청산 내역</h2>
      <table>
        <thead><tr><th>#</th><th>방향</th><th>결과</th><th>포인트</th><th>진입</th><th>청산</th></tr></thead>
        <tbody>{trades_html}</tbody>
      </table>
    </section>
  </main>
</body>
</html>
"""
    return html.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = render_html()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("쭈꾸미 상태판: http://127.0.0.1:8765", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
