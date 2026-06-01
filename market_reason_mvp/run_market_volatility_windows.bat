@echo off
setlocal

REM Run from this file's folder so relative paths work.
cd /d "%~dp0"

python market_volatility_bot.py --threshold-points=10

endlocal
