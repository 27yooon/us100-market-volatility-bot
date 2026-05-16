# Windows Quick Start

이 프로젝트는 이제 맥/윈도우 둘 다 같은 폴더 구조로 실행할 수 있다.

## 윈도우 PC로 옮길 때

1. `쭈꾸미` 폴더 전체를 그대로 복사한다.
2. 윈도우에 Python 3 설치
3. 아래 파일이 그대로 있는지 확인
   - `autotrade_mvp/.env`
   - `market_reason_mvp/market_volatility_bot.py`
   - `market_reason_mvp/run_market_volatility_windows.bat`

## 가장 쉬운 실행 방법

`market_reason_mvp/run_market_volatility_windows.bat`

이 파일을 더블클릭한다.

기본 실행값:
- 기준 종목: `^NDX`
- 감지 기준: `5분 10포인트`
- 점검 주기: `60초`

## 명령어로 직접 실행하고 싶으면

PowerShell 또는 명령 프롬프트에서:

```powershell
cd C:\Users\YOUR_NAME\Desktop\쭈꾸미\market_reason_mvp
python market_volatility_bot.py --threshold-points=10
```

## 정상 실행 확인

아래 문장이 보이면 정상:

```text
Starting loop. symbol=^NDX threshold=10.0pt poll=60s heartbeat=10m
```

## 멈추는 방법

```text
control + C
```

## 중요한 점

- 다시 처음부터 만들 필요 없음
- 같은 폴더만 복사하면 됨
- 텔레그램 설정은 `autotrade_mvp/.env` 그대로 사용
