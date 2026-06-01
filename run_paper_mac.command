#!/bin/zsh
set -e

cd "$(dirname "$0")"
mkdir -p market_reason_mvp/logs

echo
echo "[쭈꾸미] 맥 모의매매 검증 시작"
echo "기준: NQ=F / 5분봉 / 라운딩+P라인 / LEVEL 2+ / +50pt"
echo "실행 모드: 계속 감시"
echo "실제 주문 아님. 텔레그램 자동 발송 아님."
echo

caffeinate -dimsu python3 market_reason_mvp/paper_signal_runner.py --continuous --poll 60 2>&1 | tee -a market_reason_mvp/logs/paper_runner_live.log

echo
echo "종료되었습니다. 창을 닫아도 됩니다."
read "?Enter를 누르면 닫습니다." || true
