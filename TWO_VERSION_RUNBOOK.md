# 쭈꾸미 2버전 운영 안내

작성일: 2026-06-01 KST

## 결론

현재 테스트는 두 버전으로 나눈다.

1. 쭈꾸미 본버전
   - 목적: 실제 우리 매매법 검증
   - 대상: `NQ=F / US100`
   - 차트: 5분봉
   - 방식: 피봇, EMA, 라운딩, 일봉 피봇, 손익비
   - 결과: 매매 후보, 손절, 익절, 무효 조건

2. TradingAgents-CN 참고버전
   - 목적: 외부 AI 분석 구조 테스트
   - 대상: 주식 분석 프레임워크
   - 방식: 기술지표, 뉴스, 기본면, 감정, 리스크 토론
   - 결과: 구조 참고만. 쭈꾸미 매매 성과에 섞지 않는다.

## 폴더 구분

쭈꾸미 본버전:

```text
/Users/yooon/Desktop/쭈꾸미
```

TradingAgents-CN 참고버전:

```text
/Users/yooon/Desktop/쭈꾸미/external_labs/tradingagents_cn_lab/TradingAgents-CN
```

## 쭈꾸미 본버전 실행

안전한 1회 드라이런:

```text
run_zukkumi_signal_dryrun_once.command
```

안전한 1회 모의매매 체크:

```text
run_zukkumi_paper_once.command
```

밤 시간대 이어서 모의매매:

```text
run_paper_mac.command
```

기존 기록 지우고 새로 시작:

```text
reset_and_run_paper_mac.command
```

현재 이 두 실행 파일은 종료시간 없이 계속 감시 모드로 돈다.
노트북을 완전히 끄거나 재부팅하면 중단된다.

## TradingAgents-CN 참고버전 실행

현재는 설치/실행보다 구조 분석용으로 둔다.

이유:
- 원 프로젝트가 무겁다.
- Docker, DB, LLM 키, 데이터 동기화가 필요할 수 있다.
- NQ 5분봉 단타용이 아니라 주식 리포트형 구조다.

먼저 볼 파일:

```text
/Users/yooon/Desktop/쭈꾸미/external_labs/tradingagents_cn_lab/README_ZZUKKUMI_LAB.md
```

## 맥을 끄고 돌리는 경우

쭈꾸미 본버전은 Render Background Worker로 돌린다.

현재 Render 방식:
- Worker 이름 후보: `us100-dual-paper-worker`
- 실행 명령: `python market_reason_mvp/render_dual_paper_worker.py --symbol=NQ=F --poll=300 --reset`
- 텔레그램 사용 안 함
- Worker 안에서 두 모의매매 동시 실행
  - `zukkumi_rules`
  - `public_indicator_rules`

현재 예상 비용:
- 24시간 Background Worker Starter 기준 월 약 `$7`
- 이번 주만 돌리면 대략 사용 기간만큼 비례 비용으로 봄
- DB나 24시간 Web 대시보드를 붙이면 추가 비용

주의:
- Render 재개 전 프로젝트명은 반드시 `쭈꾸미 / us100-market-signal-bot`인지 확인한다.
- GitHub는 반드시 `27yooon/us100-market-volatility-bot`만 사용한다.
- TradingAgents-CN은 Render에 올리지 않는다.

## 당장 다음 순서

1. 쭈꾸미 1회 드라이런으로 현재 신호 생성이 되는지 확인한다.
2. 쭈꾸미 1회 모의매매 체크로 기록 파일이 정상 작동하는지 확인한다.
3. TradingAgents-CN은 설치하지 말고 구조 참고 문서만 본다.
4. Render로 옮기기 전, 로컬 최신 코드와 GitHub 업로드 폴더 차이를 정리한다.
5. Render에는 쭈꾸미 본버전만 올린다.
