# Market Reason MVP

## 현재 파일

- `market_volatility_bot.py`
  - 단순 5분 급변 감지용
  - 기존 안정 버전
- `market_signal_bot.py`
  - 오늘 논의한 실전 후보 버전
  - 피봇, 피보나치, 파동 위치, 거래량 감소, 봉 축소, 돌파 실패, 손익비를 같이 본다

## 새 실전 후보 버전 기준

`market_signal_bot.py`는 아래 기준을 합쳐서 신호를 만든다.

- 피봇: 중요한 위치
- 피보나치 38.2 / 50 / 61.8: 되돌림 위치
- 엘리어트 파동식 판단: 추격 금지, 충격파 이후 눌림/반등 구분
- 장대봉 이후 거래량 감소
- 봉 크기 축소
- 고점 돌파 실패 또는 저점 이탈 실패
- EMA 20 / 50 방향
- VIX, DXY, 10년물, WTI, NQ, QQQ, SOX 시장 체크
- 뉴스 키워드 헤드라인 체크
- 손절, 익절, 손익비 계산
- 점수 8점 이상만 알림

## 사전 준비

- 텔레그램 봇이 이미 연결돼 있어야 한다.
- 환경변수는 기존 파일을 그대로 쓴다:
  - `/Users/yooon/Desktop/쭈꾸미/autotrade_mvp/.env`
- 지금은 경로가 고정 맥 경로가 아니라, `쭈꾸미` 폴더 구조만 유지하면 윈도우에서도 그대로 실행 가능하다.
- 윈도우용 빠른 실행 안내:
  - `market_reason_mvp/WINDOWS_QUICKSTART.md`

## 새 버전 한 번만 테스트

```bash
python3 /Users/yooon/Desktop/쭈꾸미/market_reason_mvp/market_signal_bot.py --once --dry-run
```

## 새 버전 텔레그램 실제 전송 테스트

```bash
python3 /Users/yooon/Desktop/쭈꾸미/market_reason_mvp/market_signal_bot.py --once
```

현재 조건을 만족하는 신호가 없으면 아무 알림도 보내지 않고 아래처럼 출력된다.

```text
No qualified signal for ^NDX.
```

## 새 버전 계속 감시

로컬 컴퓨터에서 계속 켜둘 때:

```bash
python3 /Users/yooon/Desktop/쭈꾸미/market_reason_mvp/market_signal_bot.py
```

## Render 배포 기준

결제 전에 비용을 줄이기 위해 `Background Worker`가 아니라 `Cron Job` 기준으로 바꿨다.

- 5분마다 한 번 실행
- 조건 확인 후 종료
- 기본 명령:

```bash
python market_reason_mvp/market_signal_bot.py --once --symbol=NQ=F --min-level=3 --min-rr=1.30
```

Render Cron Job은 실행 시간 기준 과금이며, Render 문서 기준 Cron Job 서비스는 최소 월 $1 비용이 있다.

기본 종목은 `NQ=F`다. `^NDX`는 미국 현물지수라 장외 시간에는 데이터가 멈출 수 있어서, US100 흐름 확인에는 나스닥 선물인 `NQ=F`를 우선한다.

## 기존 단순 급변 봇

```bash
python3 /Users/yooon/Desktop/쭈꾸미/market_reason_mvp/market_volatility_bot.py --threshold-points=10
```

- `--threshold-points=10`
  - 5분에 `10포인트` 이상 움직이면 감지
  - 이 옵션을 쓰면 `% 기준` 대신 `포인트 기준`으로 본다

## 로그

결과는 여기에 쌓인다.

- `/Users/yooon/Desktop/쭈꾸미/market_reason_mvp/logs/market_reason_events.jsonl`
- `/Users/yooon/Desktop/쭈꾸미/market_reason_mvp/logs/market_signal_events.jsonl`

## 새 버전 텔레그램 메시지

지금 알림에는 아래가 같이 들어간다.

- 방향: LONG / SHORT
- 셋업 이름
- 진입 후보
- 손절
- 1차 익절
- 2차 익절
- 손익비
- 무효 조건
- 신호 근거
- 주의할 점
- 시장 체크
- 뉴스 체크
- 점수 높은 신호는 미니 차트 이미지 첨부

## 다음 단계

1. 1~2주간 드라이런 로그 확인
2. 틀린 신호가 나오면 원인 기록
3. 점수 기준과 손익비 기준 조정
4. 그다음 Render 결제/배포 진행
