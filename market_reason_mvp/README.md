# Market Reason MVP

1~2단계 목표:

`US100에 가까운 나스닥100 지수(^NDX) 5분 급변 감지 -> 텔레그램 알림`

이 단계에서는 아직 뉴스 분석은 하지 않는다.
먼저 "움직임이 컸을 때 감지해서 알려주는 파이프라인"이 정상 작동하는지 확인하고,
같은 순간의 핵심 시장 숫자도 같이 보내준다.

## 파일

- `market_volatility_bot.py`
  - 나스닥100 지수(^NDX) 5분 급변 감지
  - 텔레그램 전송
  - 중복 알림 방지
  - 함께 보는 핵심 숫자:
    - `US10Y`
    - `DXY`
    - `WTI`
    - `VIX`
    - `SOX`

## 사전 준비

- 텔레그램 봇이 이미 연결돼 있어야 한다.
- 환경변수는 기존 파일을 그대로 쓴다:
  - `/Users/yooon/Desktop/쭈꾸미/autotrade_mvp/.env`
- 지금은 경로가 고정 맥 경로가 아니라, `쭈꾸미` 폴더 구조만 유지하면 윈도우에서도 그대로 실행 가능하다.
- 윈도우용 빠른 실행 안내:
  - `market_reason_mvp/WINDOWS_QUICKSTART.md`

## 한 번만 테스트

```bash
python3 /Users/yooon/Desktop/쭈꾸미/market_reason_mvp/market_volatility_bot.py --once
```

## 계속 감시

```bash
python3 /Users/yooon/Desktop/쭈꾸미/market_reason_mvp/market_volatility_bot.py
```

기본값:
- 기준 종목: `^NDX` (`US100`에 가까운 나스닥100 지수 프록시)
- 기준 봉: `5분`
- 급변 기준: `0.40%`
- 점검 주기: `60초`

## 옵션

기준을 바꾸고 싶으면 이렇게 실행한다.

```bash
python3 /Users/yooon/Desktop/쭈꾸미/market_reason_mvp/market_volatility_bot.py --threshold=0.30 --poll=45
```

- `--threshold=0.30`
  - 5분 변동률 `0.30%` 이상 감지
- `--poll=45`
  - 45초마다 확인

종목을 바꾸고 싶으면:

```bash
python3 /Users/yooon/Desktop/쭈꾸미/market_reason_mvp/market_volatility_bot.py --symbol=QQQ --threshold=0.30
```

포인트 기준으로 테스트하고 싶으면:

```bash
python3 /Users/yooon/Desktop/쭈꾸미/market_reason_mvp/market_volatility_bot.py --threshold-points=10
```

- `--threshold-points=10`
  - 5분에 `10포인트` 이상 움직이면 감지
  - 이 옵션을 쓰면 `% 기준` 대신 `포인트 기준`으로 본다

## 로그

결과는 여기에 쌓인다.

- `/Users/yooon/Desktop/쭈꾸미/market_reason_mvp/logs/market_reason_events.jsonl`

## 현재 텔레그램 메시지

지금 알림에는 아래가 같이 들어간다.

- `NASDAQ 급변 감지`
- `변동 포인트 / 변동률`
- `US10Y`
- `DXY`
- `WTI`
- `VIX`
- `SOX`

## 다음 단계

이 단계가 잘 되면 그다음에 붙일 것:

1. `최근 뉴스 헤드라인`
2. `경제 일정`
3. `가능 / 보류 / 금지 / 원인 불명`

그 후 텔레그램 메시지를 이렇게 바꾼다.

- `급변 감지`
- `판정: 가능 / 보류 / 금지 / 원인 불명`
- `이유 1`
- `이유 2`
- `이유 3`
