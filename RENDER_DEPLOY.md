# Render Deploy

이 파일은 컴퓨터가 꺼져도 텔레그램 알림을 받기 위한 Render 배포 안내다.

## 현재 실행 대상

```bash
python market_reason_mvp/market_volatility_bot.py --threshold-points=10
```

## Render에서 넣어야 하는 환경변수

아래 2개만 Render 환경변수에 넣으면 된다.

```text
TELEGRAM_BOT_TOKEN=새로 발급한 봇 토큰
TELEGRAM_CHAT_ID=내 채팅 ID
```

## 정상 실행 문장

Render 로그에 아래가 보이면 정상이다.

```text
Starting loop. symbol=^NDX threshold=10.0pt poll=60s heartbeat=10m
```

## 멈추는 방법

Render 대시보드에서 서비스를 `Suspend` 하면 된다.

## 주의

- `.env` 파일은 Render에 올리지 않는다.
- 토큰은 Render 환경변수에만 넣는다.
- Hobby + 작은 compute면 충분하다.
