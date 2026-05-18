# 쭈꾸미 프로젝트 운영 규칙

## 프로젝트 정체성

쭈꾸미는 US100 / NDX 트레이딩 보조 프로젝트다.

주요 범위:
- TradingView Pine 신호기
- US100 / NDX 텔레그램 알림 봇
- Render / GitHub 배포
- 시장 변동, 뉴스, 지표 보조 알림

범위 밖:
- 이모저모 웹/앱 프로젝트
- 트레이딩과 무관한 웹서비스
- 사용자가 명확히 요청하지 않은 다른 프로젝트 파일 정리

## 중요한 구분

- `쭈꾸미` = US100, 트레이딩, 텔레그램 봇, Render, GitHub `us100-market-volatility-bot`
- `이모저모` = 그 외 웹/앱 작업

Render, GitHub, Chrome에서 삭제/결제/배포 전에는 반드시 프로젝트 이름을 확인한다.

## 사용자 성향

- 초보자 기준으로 아주 짧고 구체적으로 설명한다.
- 명령어는 가능하면 한 줄씩 준다.
- 같은 설명 반복을 피한다.
- 문제가 생기면 `원인 1줄 + 조치 1줄`로 먼저 답한다.

## 현재 핵심 파일

- `market_reason_mvp/market_volatility_bot.py`: 기존 단순 급변 감지 봇
- `market_reason_mvp/market_signal_bot.py`: 피봇, 피보나치, 파동, 거래량, 손익비 기반 신호 후보 봇
- `render.yaml`: Render Cron Job 배포 설정
- `autotrade_mvp/.env`: 로컬 텔레그램 토큰/채팅 ID, 절대 노출 금지

## 기본 실행

드라이런:

```bash
python3 /Users/yooon/Desktop/쭈꾸미/market_reason_mvp/market_signal_bot.py --once --dry-run
```

기본 감시 종목은 `NQ=F`다. US100과 가까운 나스닥 선물 기준이며, `^NDX`는 현물지수라 장외 시간에는 멈출 수 있다.

실제 1회 실행:

```bash
python3 /Users/yooon/Desktop/쭈꾸미/market_reason_mvp/market_signal_bot.py --once
```

기존 단순 변동 봇:

```bash
python3 /Users/yooon/Desktop/쭈꾸미/market_reason_mvp/market_volatility_bot.py --threshold-points=10
```

## 매매 신호 원칙

신호는 수익 보장이 아니라 좋은 후보만 줄이는 구조다.

중요 기준:
- 피봇은 위치
- 피보나치는 되돌림 구간
- 엘리어트 파동은 추격 금지와 파동 위치 판단
- 거래량 감소, 봉 축소, 돌파 실패는 진입 근거
- 손절/익절/손익비는 최종 통과 조건

알림에는 반드시 방향, 근거, 손절, 익절, 무효 조건이 들어가야 한다.

## 초보자용 레벨 표시

- `LEVEL 1 / 보기만`: 아무것도 하지 않기
- `LEVEL 2 / 대기`: 차트는 봐도 되지만 아직 진입 아님
- `LEVEL 3 / 진입 후보`: 차트 보고 최종 확인
- `LEVEL 4 / 강한 후보`: 우선 확인할 자리
- `LEVEL 5 / 진입 금지`: 건드리지 않기
