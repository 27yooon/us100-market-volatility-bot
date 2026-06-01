#!/bin/zsh
cd /Users/yooon/Desktop/쭈꾸미 || exit 1
python3 market_reason_mvp/market_signal_bot.py --once --dry-run --symbol=NQ=F --min-level=3 --min-rr=1.30
