#!/bin/zsh
cd /Users/yooon/Desktop/쭈꾸미 || exit 1
python3 market_reason_mvp/paper_signal_runner.py --once --symbol=NQ=F --min-level=2 --setup-contains='라운딩,P라인' --profit-points=50
