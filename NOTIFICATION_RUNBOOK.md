# 쭈꾸미 알림 운영 기준

Render 모의매매 결과를 사용자가 매번 Codex에게 묻지 않아도 확인할 수 있게 하는 알림 기준이다.

## 알림 채널

| 채널 | 용도 |
|---|---|
| Telegram | 즉시 알림, 23시 중간 보고, 06:10 최종 보고 |
| Notion | 거래/후보/일일 보고 누적 기록 |
| Render 로그 | 원본 로그와 장애 확인 |

## Telegram 알림

Render 환경변수에 아래 값이 있어야 동작한다.

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

선택 설정:

```text
TELEGRAM_PAPER_NOTIFY=true
```

`TELEGRAM_PAPER_NOTIFY=false`로 두면 텔레그램 알림을 끈다.

## 즉시 알림

아래 이벤트가 발생하면 텔레그램을 보낸다.

| 이벤트 | 내용 |
|---|---|
| `OPEN` | 모의매매 진입 |
| `CLOSE` | 모의매매 청산 |

즉시 알림 대상 전략:

| 전략 | 알림 |
|---|---|
| 쭈꾸미 원본 | 보냄 |
| 기본지표 | 보냄 |
| 버크매매 | 보냄 |
| 점수제 관찰 | 보내지 않음 |

점수제 관찰은 실제 진입이 아니므로 즉시 알림 대상이 아니다.

## 일일 보고

| 시간 | 이름 | 내용 |
|---|---|---|
| 23:00 KST | 중간 보고 | 오늘 현재까지 진입/보유/손익, 버크매매 초반 상태 |
| 06:10 KST | 최종 보고 | 전날 밤 미국장 기준 총 거래/승패/손익/후보 요약 |

중복 방지:
- 같은 기준일의 같은 보고는 한 번만 보낸다.
- 상태 파일의 `daily_reports_sent`에 보낸 키를 저장한다.

## Notion 기록

Notion은 Codex/ChatGPT 커넥터가 아니라 프로젝트 API/env만 사용한다.

필요 환경변수:

```text
NOTION_API_TOKEN
NOTION_DATABASE_ID
```

기록 이벤트:
- `OPEN`
- `CLOSE`
- `HEARTBEAT`
- `DAILY_REPORT`
- `ERROR`

## Render 로그 확인

Render 로그:

https://dashboard.render.com/worker/srv-d8eomv6k1jcs73a6vro0/logs

찾을 문구:

```text
[TODAY_STATUS]
telegram_open=ok
telegram_close=ok
telegram_daily_report=ok
```

## 주의

- 모든 알림은 실거래가 아니라 Render 모의매매 기준이다.
- 후보/관찰 이벤트는 너무 많으므로 텔레그램 즉시 알림으로 보내지 않는다.
- 텔레그램이 실패해도 모의매매 기록 자체는 계속된다.
- Notion env가 없으면 Notion 기록은 건너뛴다.

