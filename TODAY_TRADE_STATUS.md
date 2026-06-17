# 오늘 매매 여부 확인 방법

사용자가 매번 Codex에게 묻지 않아도 오늘 진입 여부를 확인할 수 있게 정리한 문서다.

## 제일 빠른 확인 위치

Render 로그:

https://dashboard.render.com/worker/srv-d8eomv6k1jcs73a6vro0/logs

로그에서 아래 문구를 찾는다.

```text
[TODAY_STATUS]
```

예시:

```text
[TODAY_STATUS] 2026-06-08 오늘 매매 없음 | zukkumi_original 진입 0 / 보유 0 / 손익 +0.0pt | indicator_basic 진입 0 / 보유 0 / 손익 +0.0pt | orb_paper 진입 0 / 보유 0 / 손익 +0.0pt
```

## 보는 법

| 표시 | 뜻 |
|---|---|
| `오늘 매매 없음` | 오늘 실제 모의매매 진입이 아직 없음 |
| `오늘 진입 1회` | 오늘 실제 모의매매가 1번 들어감 |
| `보유 1건` | 아직 청산되지 않은 모의 포지션이 있음 |
| `청산 1건` | 오늘 청산된 거래가 있음 |
| `손익 +50.0pt` | 오늘 청산된 거래 기준 손익 |

## 전략 이름

| 이름 | 뜻 |
|---|---|
| `zukkumi_original` | 쭈꾸미 원본 |
| `indicator_basic` | 기본지표 |
| `orb_paper` | 버크매매 |
| `score_watch` | 점수제 관찰. 실제 매매 아님 |

## 주의

- `score_watch`는 관찰용이므로 진입 수가 있어도 실제 모의매매 진입으로 보지 않는다.
- 실제 모의매매 여부는 `쭈꾸미 원본`, `기본지표`, `버크매매`를 기준으로 본다.
- Render heartbeat가 멈추면 오늘 상태도 갱신되지 않는다.

