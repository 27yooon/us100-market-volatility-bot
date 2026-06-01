# 쭈꾸미 현재 상태

이 파일은 대화 반복을 줄이기 위한 현재 기준표다.

## 대화방 역할

- 본작업방: 전략, 신호 기준, 코드 수정, 실패 분석, 계획 결정.
- 봇전용방: 터미널 실행, 봇 켜기/끄기, Render 상태 확인 같은 운영 작업.
- 앞으로 중요한 결정은 본작업방에 남긴다.
- 봇전용 요약 파일: `BOT_ROOM_SUMMARY.md`
- 채팅방이 context 오류로 멈출 수 있으므로 중요한 작업은 파일에 남긴다.
- 새 채팅이나 후임 Codex는 먼저 `RECOVERED_CONTEXT.md`와 이 파일을 읽는다.
- 2026-05-27 결정:
  - 오늘 이후 윈도우 Codex/윈도우 PC 모의매매는 사용하지 않는다.
  - 앞으로 쭈꾸미 진행은 이 맥 Codex 기준으로 한다.
  - 윈도우 연동/GitHub 왕복 자동화는 우선순위에서 제외한다.
- 2026-05-28 맥 실행 준비:
  - 맥 전용 실행 안내 파일: `MAC_PAPER_RUN.md`
  - 새 검증 시작 파일: `reset_and_run_paper_mac.command`
  - 이어서 실행 파일: `run_paper_mac.command`
  - 두 파일 모두 `caffeinate`로 맥 잠자기를 막고 `paper_runner_live.log`에 로그를 저장한다.
- 2026-05-28 23:38 KST:
  - 맥 모의매매 감시를 `screen` 세션 `zzukkumi_paper`로 시작했다.
  - 기준: `NQ=F / 5분봉 / 라운딩 / LEVEL 2+ / +50pt`.
  - 종료 예정: `2026-05-29 02:00 KST`.
  - 현재 실제 주문/텔레그램 자동 발송은 하지 않는다.
  - 상태 파일: `market_reason_mvp/logs/paper_signal_state.json`
  - 로그 파일: `market_reason_mvp/logs/paper_runner_live.log`
- 2026-05-29 00:41 KST:
  - 시각 확인용 로컬 상태판을 추가했다.
  - 파일: `market_reason_mvp/paper_status_dashboard.py`
  - 실행 세션: `screen` 세션 `zzukkumi_dashboard`
  - 주소: `http://127.0.0.1:8765`
  - 15초마다 자동 새로고침하며 감시 상태, 열린 포지션, 승패/포인트, 최근 로그를 보여준다.
- 2026-05-29 텔레그램 상태 알림:
  - 텔레그램은 매매 신호 자동 발송보다 상태 알림 용도로 우선 사용한다.
  - 상태 알림 파일: `market_reason_mvp/paper_status_notify.py`
  - 수동 전송 명령:
    - `python3 /Users/yooon/Desktop/쭈꾸미/market_reason_mvp/paper_status_notify.py`
  - 포함 내용: 감시 중/꺼짐, 열린 포지션, 매매 횟수, 승패, 총 포인트, 최근 로그.
  - 2026-05-29 00시대 수동 상태 알림 전송 성공.
- 2026-05-28 밤~2026-05-29 02:00 KST 모의매매 결과:
  - 감시 기간: `2026-05-28 23:38 KST` ~ `2026-05-29 02:00 KST`
  - 기준: `NQ=F / 5분봉 / 라운딩 / LEVEL 2+ / +50pt`
  - 결과: 매매 0회, 0승 0패, 총 `+0.00pt`
  - 원인 해석: 일봉 피봇 필터를 추가한 뒤 조건이 엄격해져 진입 후보가 없었다.
  - 다음 점검: 후행 차트로 실제 놓친 좋은 자리가 있었는지 확인하고, 필요하면 `LEVEL 1 관찰 후보`를 별도 기록 대상으로 둘지 검토한다.
- 2026-05-29 P라인 미진입 원인 분석:
  - 감시 구간 안에서 일봉 P라인 `30101.25` 근처 접근은 `23:40`, `23:45` 두 번 있었다.
  - `00:00`에는 코드상 `P라인 바닥 횡보 롱` 원시 후보가 `LEVEL 4`로 만들어졌다.
  - 하지만 확인봉 조건을 통과하지 못해 최종 신호가 되지 않았다.
  - 현재 모의매매 필터가 `--setup-contains=라운딩`이라 P라인 후보는 애초에 기록 대상에서 제외된다.
  - 같은 구간에서 필터를 풀면 `00:40`에 `상승 피로 숏 확인 LEVEL 3` 1회가 잡히지만, 후행 결과는 `-39.25pt` 손실이었다.
  - 결론: 어제 0회는 감시 오류가 아니라 `라운딩 전용 필터 + 확인봉 조건` 때문이다.
- 2026-05-29 P라인 반등 롱 반영:
  - 새 매매법 `P라인 반등 롱 확인`을 추가했다.
  - 의미: 일봉 P라인 근접 후 아래 확정 이탈 없이 다시 회복하는 빠른 롱 자리.
  - 기존 `P라인 바닥 횡보 롱`보다 빠르게 잡는다.
  - 모의매매 기본 필터를 `라운딩`에서 `라운딩,P라인`으로 변경했다.
  - 2026-05-28 KST 후행 평가에서 `P라인 반등 롱 확인`은 4회, 3승 1패였다.
  - 어제 사용자가 말한 `23:45 P라인 근접 후 회복 롱`은 새 로직에서 `LONG LEVEL 2`, 후행 `WIN +50pt`로 잡힌다.

## 다른 채팅 내용

- Codex는 다른 채팅방의 과거 대화를 자동으로 가져올 수 없다.
- 봇전용방에서 중요한 내용이 있으면 사용자가 복사/캡처로 보내야 한다.
- 받은 내용은 이 파일이나 관련 로그에 요약 저장한다.
- 앞으로 모든 중요한 변경은 채팅 기억에만 두지 않는다.
- 기록할 것:
  - 수정 파일
  - 테스트 명령
  - 테스트 결과
  - GitHub 반영 여부
  - Render 반영 여부
  - 다음 작업

## 현재 봇 상태

- Render Cron Job `us100-market-signal-bot`은 일시중지 상태다.
- 텔레그램 자동 신호 발송은 재정비 전까지 재개하지 않는다.
- 샘플 메시지는 수동 테스트용으로만 보낸다.
- 초보자 모의매매 기록기는 로컬에서만 실행한다. 텔레그램 전송과 실제 주문은 하지 않는다.
- GitHub 저장소: `27yooon/us100-market-volatility-bot`
- Render 방식: 비용 때문에 `Background Worker`가 아니라 `Cron Job`
- Render 명령:
  - `python market_reason_mvp/market_signal_bot.py --once --symbol=NQ=F --min-level=3 --min-rr=1.30`
- 2026-05-22 계정/권한 확인:
  - Chrome GitHub 로그인 계정은 `27yooon`.
  - Codex GitHub 앱 계정은 `Inwest1997`로 잡혀 있으며, 쭈꾸미 저장소에는 push 권한이 없다.
  - 쭈꾸미 GitHub 작업은 `27yooon` 기준으로 해야 한다.
  - 로컬 Git 원격은 `https://github.com/27yooon/us100-market-volatility-bot.git`.
  - 로컬 Git `push --dry-run`은 성공했다.
- 2026-05-22 Render 확인:
  - Render 대시보드 접속 가능: `https://dashboard.render.com`
  - 워크스페이스: `J's workspace`
  - 서비스 URL: `https://dashboard.render.com/cron/crn-d866d7p9rddc73f1op80`
  - 서비스 상태: `Suspended by you`
  - Billing: Hobby 플랜, 결제수단 등록됨.
  - 검색창에서 `us100`을 검색하면 `us100-market-signal-bot`가 나온다.
- 2026-05-22 Telegram 확인:
  - 로컬 `.env`에 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` 설정 있음.
  - Bot API 확인 성공.
  - 봇 이름: `us100 signal bot`
  - 봇 username: `us100_yoon_bot`
  - 연결 채팅: private `Yoon J`
  - 과거 로그에 `telegram_ok: true` 전송 성공 기록 다수 있음.
  - 현재 Render 중지는 텔레그램 문제가 아니라 신호 검증 때문에 일부러 멈춘 상태다.
- 2026-05-31 GitHub/자료 점검:
  - GitHub 원격 `27yooon/us100-market-volatility-bot`의 최신 커밋은 `ebfea49 Improve beginner signal alert formatting`.
  - 원격에는 오래된 배포용 파일만 있다.
  - 최근 만든 핵심 자료는 아직 GitHub에 없다:
    - `TRADING_METHODS.md`
    - `MAC_PAPER_RUN.md`
    - `market_reason_mvp/paper_signal_runner.py`
    - `market_reason_mvp/paper_status_dashboard.py`
    - `market_reason_mvp/paper_status_notify.py`
    - 최신 `market_reason_mvp/market_signal_bot.py`의 라운딩/P라인 반등 로직
  - 즉 현재 성과가 체감되지 않는 큰 이유 중 하나는 GitHub/Render 기준과 로컬 실험 기준이 분리되어 있기 때문이다.

## 현재 신호 기준

- 종목: US100 / NQ=F
- 기준 차트: 5분봉
- 핵심: 차트 우선, 뉴스는 위험 필터
- 목표 빈도: 하루 2~3회
- 채점 기준: 진입가 기준 +50포인트가 손절/무효보다 먼저 오면 WIN
- 재개 기준: 드라이런 10개 중 8개 이상 성공
- 2026-05-25 전략 보완:
  - 피봇라인 터치만 기다리면 매매 후보가 너무 적다.
  - 새 후보: `라운딩 바닥 롱`, `라운딩 천장 숏`.
  - 의미: 상승/하락이 멈춘 뒤 봉이 짧아지고 둥글게 말리면, 직전 진행 방향의 반대 매매를 확인한다.
  - 이 후보는 피봇/주요 지지저항 터치를 필수로 보지 않는다.
  - 대신 반드시 확인봉, 손절, 익절, 무효 조건이 있어야 한다.
  - 아직 실전/Render 재개 기준이 아니다. 먼저 드라이런과 모의매매로 검증한다.
- 2026-05-28 추가 보완:
  - 라운딩 후보도 일봉 피봇 위치를 반드시 참고한다.
  - 일봉 `P / R1 / R2 / S1 / S2` 근처면 방향에 맞는 근거로 반영한다.
  - 일봉 피봇과 멀거나 일봉 P 위/아래 방향이 안 맞으면 주의로 반영해 레벨을 낮춘다.
  - 2026-05-27 라운딩 숏 3개는 이 필터 후 `LEVEL 2`에서 제외되고 `LEVEL 1`로 낮아졌다.

## 초보자 모의매매

- 파일: `market_reason_mvp/paper_signal_runner.py`
- 목적: 주식/매매를 모르는 초보자가 신호만 따라갔다고 가정하고 실제 주문 없이 포인트 손익을 기록한다.
- 2026-05-25 변경:
  - 기존 기본 필터가 `P라인 바닥`이라 신호가 거의 안 나왔다.
  - 기본 테스트 필터를 `라운딩`으로 변경했다.
  - 기본 `--min-level`을 4에서 2로 낮췄다.
  - 이유: 라운딩은 아직 검증 단계라 강한 후보만 보지 말고 대기 후보까지 기록해야 한다.
  - 윈도우에서 다시 돌릴 때 새 라운딩 후보가 잡히는지 확인한다.
  - 아직 GitHub 업로드용 폴더 `_보관/us100_render_upload`와 Render에는 반영하지 않았다.
  - 이유: 먼저 로컬/윈도우 모의매매로 라운딩 후보를 검증해야 한다.
- 2026-05-27 후행 점검:
  - GitHub `27yooon/us100-market-volatility-bot`에는 윈도우 Codex가 올린 새 결과 파일이 없었다.
  - 로컬에 남은 실제 모의매매 상태도 구버전 기준이며 청산 매매 0회였다.
  - 같은 5일 데이터를 후행 시뮬레이션하면:
    - 구버전 `P라인 바닥 / LEVEL 4`: 0회, +0.00pt
    - 새 `라운딩 / LEVEL 2`: 5회 청산, 3승 2패, 총 +70.50pt, 평균 +14.10pt
  - 새 라운딩 결과는 아직 후행 평가일 뿐이고 실시간 검증/배포 기준은 아니다.
- 현재 실행 위치:
  - 사용자가 정정함.
  - 2026-05-27부터 윈도우 Codex는 더 이상 기준 운영 환경으로 보지 않는다.
  - 앞으로 모의매매, 후행 평가, 코드 수정, GitHub/Render 준비는 이 맥 Codex에서 진행한다.
  - 이 맥에 남아 있는 과거 로그는 참고용이며, 새 검증은 새로 시작한다.
- 윈도우 결과를 가져오면 확인할 파일:
  - `market_reason_mvp/logs/paper_signal_state.json`
  - `market_reason_mvp/logs/paper_trades.csv`
  - `market_reason_mvp/logs/paper_trades.jsonl`
  - `market_reason_mvp/logs/paper_runner_live.log`
- 기본 기준:
  - `NQ=F`
  - 5분봉
  - `LEVEL 2` 이상
  - `라운딩` 패턴 우선
  - 목표 `+50pt`
  - 한 번에 1포지션만
- 실행:
  - 첫날 새로 시작: `reset_and_run_paper_mac.command`
  - 다음날부터 이어서 실행: `run_paper_mac.command`
  - 터미널 직접 실행: `python3 /Users/yooon/Desktop/쭈꾸미/market_reason_mvp/paper_signal_runner.py --poll 60`
- 종료:
  - 기본은 다음 `02:00 KST`
  - 권장 실행 시간은 매일 `22:00~02:00 KST`
- 결과 파일:
  - `market_reason_mvp/logs/paper_signal_state.json`
  - `market_reason_mvp/logs/paper_trades.jsonl`
  - `market_reason_mvp/logs/paper_trades.csv`
- 해석:
  - 결과표의 `총 포인트`와 `매매당 평균`만 먼저 본다.
  - 매매가 0회면 신호가 없었던 것이지 오류가 아니다.

## 현재까지 결론

- 기존 로직은 50포인트 기준으로 최근 10개 중 5개, 최근 20개 중 8개 성공이라 아직 부족하다.
- 사용자가 말한 `바닥 형성 후 횡보` 패턴은 코드에 `바닥 횡보 롱`으로 추가했다.
- `바닥 횡보 롱`만 따로 보면 +50포인트 기준:
  - 1시간 안: 20개 중 5개 성공
  - 2시간 안: 20개 중 8개 성공
  - 3시간 안: 20개 중 13개 성공
  - 4시간 안: 20개 중 15개 성공, MISS 0개
- 결론: 이 패턴은 빠른 스캘핑보다 3~4시간까지 열어두는 반등/지속 매매에 더 가깝다.
- `MISS`는 실패로 고정하지 않는다. 시간이 더 지나 +50포인트가 나오면 `WIN`으로 재분류한다.
- 4시간 기준으로 다시 보면 전체 신호는 최근 20개 중 12개 성공, MISS 0개로 통과했다.
- 다만 최근 10개는 7개 성공이라 기준 8개에는 1개 부족하다.
- 신호 종류별 4시간 기준:
  - `바닥 횡보 롱 확인`: 6승 2패, 승률 75.0%
  - `하락 피로 롱 확인`: 9승 5패, 승률 64.3%
  - `피보 눌림 롱 확인`: 7승 8패 1미스, 승률 43.8%
  - `피보 반등 숏 확인`: 9승 11패 1미스, 승률 42.9%
  - `상승 피로 숏 확인`: 9승 12패, 승률 42.9%
- 결론: 자동 발송을 재개하더라도 전체 신호가 아니라 `바닥 횡보 롱` 위주로 제한해야 한다.
- 사용자가 강조한 `P라인 터치/근접 후 바닥 횡보`는 `P라인 바닥 횡보 롱`으로 별도 분리했다.
- 확인용 날짜:
  - `2026-04-20 KST`
  - 신호: `2026-04-20 21:40 KST LONG L4`
  - P라인: `26716.75`
  - 진입: `26733.00`
  - 손절: `26705.57`
  - +50pt 목표: `26783.00`
  - 결과: `WIN`
- 피봇 중심은 유지한다.
- `LONG / SHORT` 라벨 스타일은 유지한다.
- 텔레그램 메시지는 5초 안에 읽히는 짧은 카드형 문구로 유지한다.
- 알림 첫 줄은 이모지로 즉시 구분한다.
  - `🟢` 롱
  - `🔴` 숏
  - `❌` 진입 아님
- 신호 후보에는 차트 이미지를 붙인다.
- 봇전용 요약과 본작업방 기준은 거의 일치한다.
- 차이점:
  - 봇전용은 실행/배포/토큰/Render 운영 기록이 많다.
  - 본작업방은 최신 전략 변경, 실패 원인, 프리장 다듬기 패턴, 모바일 알림 형식이 더 최신이다.

## 다음에 넣을 핵심 후보

- 피봇/전고점/전저점 위치
- 스윕 후 회복
- 바닥 형성 후 횡보
  - 단순히 레벨에 닿은 것이 아니라, 아래로 한 번 밀린 뒤 더 이상 저점을 깨지 못하고 작은 봉으로 버티는 구간
  - 핵심은 `바닥 찍음 -> 횡보 -> 매도세 약화 -> 회복/돌파`
- 봉 크기 축소
- 다음 봉 확인
- 프리장 스윕 후 다듬기 반전
- `WATCH`와 `ENTRY` 분리
  - `WATCH`: 중요한 자리 접근 알림
  - `ENTRY`: 반응 확인 후 진입 후보

## 넣되 보조로만 쓸 것

- VWAP
- EMA 20/50 뭉침
- 피보나치 되돌림
- 거래량 감소
- 한국어 뉴스 위험 태그

## 당분간 하지 말 것

- 텔레그램 자동 발송 재개
- LEVEL 3을 바로 진입 신호처럼 표현
- `안 들어가도 됨`처럼 애매한 표현
- 영어 뉴스 원문 나열
- PH/PL 복잡한 표시 재도입
- 한 번에 여러 로직 수정
- 실패 원인 분석 없이 지표만 계속 추가
- 피봇만 기준으로 단독 진입 신호 생성
- 강한 추세장에서 단순 반전 숏/롱을 쉽게 발송

## 알림 인터페이스 원칙

- 텔레그램 문구 기준 파일: `market_reason_mvp/TELEGRAM_PROMPT.md`
- 사용자가 3초 안에 이해해야 한다.
- 첫 줄은 방향과 상태만:
  - `🟢 롱 진입 가능 후보`
  - `🔴 숏 진입 가능 후보`
  - `❌ 지금 진입 금지`
- 신호 알림은 아래 순서만 유지한다:
  - 지금 할 일
  - 조건
  - 진입
  - 무효
  - 1차 목표
  - 유형
  - 시간
  - 근거 2개
- 뉴스 원문, 긴 설명, 애매한 문장, 많은 보조지표 나열은 빼야 한다.
- `진입 가능 후보`에도 반드시 `손절 가능하면 소액`을 붙여 과신을 막는다.

## 다음 작업 우선순위

1. `WATCH`와 `ENTRY`를 코드/메시지에서 분리한다.
2. 프리장 스윕 후 다듬기 반전 조건을 채점기에 넣는다.
3. `+50pt` 기준으로 최근 10개를 다시 평가한다.
4. 10개 중 8개 이상이 되기 전까지 Render 자동 발송은 재개하지 않는다.

## 외부 프로젝트 분리 테스트 원칙

- 외부 GitHub 프로젝트 실험실 문서: `/Users/yooon/Desktop/쭈꾸미/EXTERNAL_LABS.md`
- 외부 실험 폴더: `/Users/yooon/Desktop/쭈꾸미/external_labs`
- TradingAgents-CN 실험 폴더: `/Users/yooon/Desktop/쭈꾸미/external_labs/tradingagents_cn_lab`
- 쭈꾸미 본 코드와 외부 프로젝트 코드는 분리해서 테스트한다.
- 외부 프로젝트에서 좋은 구조가 보이면 바로 실전 코드에 섞지 말고, 먼저 아이디어만 추출해서 쭈꾸미 방식으로 다시 구현한다.
- 2026-05-31 Agent Swarm 결론:
  - TradingAgents-CN은 주식 중장기 분석 리포트형 프레임워크다.
  - 쭈꾸미는 NQ=F 5분봉 단타 후보 검증용이다.
  - 가져올 것은 코드가 아니라 `역할 분리`, `리스크 Judge`, `최종 신호 구조화`다.
  - 세부 내용은 `/Users/yooon/Desktop/쭈꾸미/EXTERNAL_LABS.md`의 `Agent Swarm 분석 결과`를 본다.

## 맥을 켜지 않고 운영하는 방법

- 결론: 맥이 꺼져도 감시하려면 Render, VPS, GitHub Actions 같은 외부 서버가 필요하다.
- 2026-06-01 변경: Render는 Cron이 아니라 Background Worker로 운영하는 쪽이 맞다.
- 이유: Render Cron은 persistent disk를 쓸 수 없어, 진입 후 승패 추적 상태 저장에 불리하다.
- 현재 `render.yaml`은 Render Background Worker로 아래 명령을 실행하는 구조다.
  - `python market_reason_mvp/render_dual_paper_worker.py --symbol=NQ=F --poll=300 --reset`
- 텔레그램은 사용하지 않는다.
- Worker 안에서 두 개의 모의매매를 동시에 돌린다.
  - `zukkumi_rules`: 우리가 정한 피봇/EMA/라운딩/P라인 규칙
  - `public_indicator_rules`: TradingAgents-CN에서 참고한 MA/EMA, RSI, Bollinger, ATR식 공개 기술지표 참고 규칙
- Render 서비스 `us100-market-signal-bot`은 현재 사용자가 일시중지한 상태다.
- 새 Worker 이름 후보는 `us100-dual-paper-worker`다.
- 추천 순서:
  1. 로컬 최신 코드를 GitHub `27yooon/us100-market-volatility-bot`에 안전하게 반영
  2. Render에서 Background Worker를 켜기
  3. 이번 주는 Render 로그와 Worker 내부 상태 파일 기준으로 모의매매 결과 확인
  4. 자동 실전매매는 검증 10회 이상 통과 전까지 금지

## Render 비용 추정

- 확인일: 2026-05-31
- 공식 Render 가격표 기준:
  - Hobby workspace: `$0/mo + compute`
  - Cron Jobs: `Starter $0.00016/minute`, Cron Jobs는 `$1/mo`부터 시작
  - Web/Worker를 24시간 켜두는 Starter 서비스는 `$7/mo`
- 현재 `render.yaml`은 5분마다 1회 실행이므로 24시간 기준 하루 288회 실행.
- 예상 비용:
  - 1회 10초 실행: 약 `$0.23/mo`, 단 최소 과금 때문에 대략 `$1/mo` 예상
  - 1회 30초 실행: 약 `$0.69/mo`, 단 최소 과금 때문에 대략 `$1/mo` 예상
  - 1회 1분 실행: 약 `$1.38/mo`
  - 1회 2분 실행: 약 `$2.76/mo`
  - 1회 5분 실행: 약 `$6.91/mo`
- 22:00~06:00 KST처럼 하루 8시간만 돌리면 위 금액의 약 1/3 수준.
- 단, 모의매매 결과 저장용으로 유료 DB나 24시간 Web/Worker를 추가하면 별도 비용이 붙는다.
- 쭈꾸미 추천:
  - 모의매매 승패 추적은 Cron보다 Background Worker 사용
  - Background Worker Starter는 24시간 상시 실행 기준 대략 `$7/mo` 수준으로 잡기
  - 이번 주만 돌리면 사용 기간만큼 비례 비용으로 볼 것
  - DB/대시보드는 아직 붙이지 않기

## 2버전 테스트 준비 상태

- 작성일: 2026-06-01 KST
- 운영 안내: `/Users/yooon/Desktop/쭈꾸미/TWO_VERSION_RUNBOOK.md`
- 쭈꾸미 안전 1회 드라이런: `/Users/yooon/Desktop/쭈꾸미/run_zukkumi_signal_dryrun_once.command`
- 쭈꾸미 안전 1회 모의매매 체크: `/Users/yooon/Desktop/쭈꾸미/run_zukkumi_paper_once.command`
- TradingAgents-CN 로컬 클론:
  - `/Users/yooon/Desktop/쭈꾸미/external_labs/tradingagents_cn_lab/TradingAgents-CN`
  - 원격: `https://github.com/hsliuping/TradingAgents-CN.git`
  - 확인 커밋: `cdd0316`
- TradingAgents-CN 쭈꾸미 실험 안내:
  - `/Users/yooon/Desktop/쭈꾸미/external_labs/tradingagents_cn_lab/README_ZZUKKUMI_LAB.md`
- 현재 단계:
  - 외부 프로젝트는 구조 참고용으로만 둔다.
  - 쭈꾸미 본버전만 실행/검증 대상이다.
  - Render/GitHub 배포는 아직 하지 않았다.
- 2026-06-01 09:05 KST 확인:
  - `run_zukkumi_signal_dryrun_once.command` 정상 실행
  - 결과: `❌ 지금 진입 금지`, NQ=F 30481.00
  - `run_zukkumi_paper_once.command` 정상 실행
  - 결과: 신호 없음, 매매 0회, 총 포인트 +0.00pt
- 2026-06-01 09:40 KST GitHub 업로드 폴더 준비:
  - Git 저장소: `/Users/yooon/Desktop/쭈꾸미/_보관/us100_render_upload`
  - 원격: `https://github.com/27yooon/us100-market-volatility-bot.git`
  - GitHub push 완료: `main` 브랜치에 반영. 정확한 커밋은 업로드 폴더에서 `git log -1 --oneline`으로 확인.
  - 포함: 최신 `market_signal_bot.py`, paper runner/dashboard/notify, 운영 문서, 2버전 실행 문서
  - 제외: `.env`, 실제 텔레그램 토큰/채팅ID, TradingAgents-CN 전체 외부 코드
  - 검증: `py_compile` 통과, 드라이런 정상 실행
  - GitHub push: 완료
  - 아직 하지 않은 것: Render 대시보드 로그인 후 Worker 생성/재개

## Render 두 모의매매 Worker

- 작성일: 2026-06-01 KST
- GitHub: `https://github.com/27yooon/us100-market-volatility-bot.git`
- Render 방식: Background Worker
- Render 서비스 이름 후보: `us100-dual-paper-worker`
- 실행 파일: `market_reason_mvp/render_dual_paper_worker.py`
- 실행 명령:
  - `python market_reason_mvp/render_dual_paper_worker.py --symbol=NQ=F --poll=300 --reset`
- 텔레그램:
  - 사용하지 않음
- 동시에 돌리는 모의매매:
  - `zukkumi_rules`: 피봇/EMA/라운딩/P라인, +50pt
  - `public_indicator_rules`: TradingAgents-CN에서 참고한 MA/EMA, RSI, Bollinger, ATR 기술지표형 룰, +50pt
- 로컬 검증:
  - `python3 market_reason_mvp/render_dual_paper_worker.py --once --reset --poll=30`
  - 정상 실행, HEARTBEAT 출력 확인
- 비용 메모:
  - Cron은 저렴하지만 persistent disk 사용 불가라 모의매매 보유/승패 추적에 부적합
  - Background Worker Starter는 24시간 기준 월 약 `$7`
  - 이번 주만 돌리면 기간 비례로 예상
- 현재 블로커:
  - 없음. Render Worker 생성 및 실행 확인 완료.

## Render 실행 확인

- 확인 시각: 2026-06-01 22:39~22:40 KST
- Render 서비스:
  - 이름: `us100-dual-paper-worker`
  - 타입: Background Worker
  - 서비스 ID: `srv-d8eomv6k1jcs73a6vro0`
  - 로그 URL: `https://dashboard.render.com/worker/srv-d8eomv6k1jcs73a6vro0/logs`
  - 상태: `Live`
  - 플랜: Starter `$7/month`
  - GitHub: `27yooon/us100-market-volatility-bot`
  - 브랜치: `main`
  - 배포 커밋: `93edd4f Prepare zukkumi two-version testing`
- 실제 실행 로그:
  - `==> Running 'python market_reason_mvp/render_dual_paper_worker.py --symbol=NQ=F --poll=300 --reset'`
  - `2026-06-01 22:39:50 KST START`
  - `2026-06-01 22:39:51 KST HEARTBEAT`
  - 가격: `NQ=F 30338.0`
  - `zukkumi_rules`: trades 0, wins 0, losses 0, pnl 0, open false
  - `public_indicator_rules`: trades 0, wins 0, losses 0, pnl 0, open false
- 텔레그램:
  - 사용 안 함
- 후속 체크:
  - Codex heartbeat `쭈꾸미 Render 24시간 감시 상태 확인`
  - 2026-06-06 06:00 KST까지 약 6시간마다 Render/로컬 상태 확인

## 현재 실행 중인 모의매매 감시

- 시작: 2026-06-01 21:14 KST
- 실행 위치: 이 맥 로컬
- screen 세션: `zzukkumi_paper`
- 명령:
  - `caffeinate -dimsu python3 -u market_reason_mvp/paper_signal_runner.py --reset --continuous --poll 60`
- 상태 파일:
  - `/Users/yooon/Desktop/쭈꾸미/market_reason_mvp/logs/paper_signal_state.json`
- 로그 파일:
  - `/Users/yooon/Desktop/쭈꾸미/market_reason_mvp/logs/paper_runner_live.log`
- 종료 예정:
  - 없음. 계속 감시 모드.
- 이번 주 검증 기준:
  - 2026-06-01 21:14 KST부터 2026-06-06 06:00 KST까지 24시간 감시
  - 미국장 금요일 마감 후 1차 결과 평가
  - 그 전에는 Render/Telegram 자동 발송 재개 금지
- 현재 확인:
  - 2026-06-01 21:14:50 KST 대기/신호 없음
  - 2026-06-01 21:15:54 KST 대기/신호 없음
  - 2026-06-01 21:21:13 KST 대기/신호 없음
- 후속 체크:
  - Codex heartbeat `쭈꾸미 24시간 감시 상태 확인`
  - 2026-06-06 06:00 KST까지 약 6시간마다 상태 확인
- 주의:
  - 이 실행은 맥 로컬 실행이다.
  - Render 24시간 실행은 아직 켜지 않았다.
  - 노트북을 완전히 끄거나 재부팅하면 중단된다.
  - 종료가 필요하면 `screen -S zzukkumi_paper -X quit`로 끈다.

## 외부 참고 사례: TradingAgents-CN

- 확인 시각: 2026-05-31 18:56 KST
- GitHub: https://github.com/hsliuping/TradingAgents-CN
- 성격: 실시간 자동매매 봇이라기보다, 여러 LLM 에이전트가 한 종목을 분석하고 토론해서 `매수/보유/매도` 의견과 리스크를 만드는 주식 리서치/학습 프레임워크.
- 저장소 설명상 목적: 중국어 사용자를 위한 다중 에이전트/대형언어모델 기반 주식 분석 학습 플랫폼. 실전 매매 지시를 제공하지 않고 연구/교육용이라고 명시함.
- 구조:
  - `market_analyst`: 이동평균, MACD, RSI, 볼린저밴드 등 기술지표 분석
  - `news_analyst`, `social_media_analyst`, `fundamentals_analyst`: 뉴스/감정/기본면 분석
  - `bull_researcher`, `bear_researcher`: 강세/약세 논리 토론
  - `risk_mgmt`: 공격적/중립/보수 리스크 토론
  - `trader`: 최종 매수/보유/매도, 목표가, 신뢰도, 위험점수 작성
- 쭈꾸미에 바로 가져올 점:
  - 진입 신호를 바로 내기 전에 `찬성 근거`, `반대 근거`, `리스크 경고`를 분리해서 점수화한다.
  - 텔레그램에는 최종 결론만 보내되, 내부 로그에는 강세/약세/보수 의견을 남긴다.
  - 우리처럼 5분봉 단타에는 그대로 쓰기보다, `진입 판단 회의 구조`만 참고한다.
- 판단 근거:
  - 기술지표: MA/EMA, MACD, RSI, Bollinger Band, ATR, KDJ, 지지/저항
  - 기본면: P/E, P/B, DCF, 업종 평균 밸류에이션, 재무상태
  - 뉴스: Google News, Finnhub 뉴스, 실시간 뉴스 도구
  - 감정/여론: Reddit/소셜미디어 감정 보고서
  - 데이터 소스: Tushare, AkShare, BaoStock, Yahoo Finance/yfinance, Finnhub 등
  - 의사결정 방식: 강세 분석가와 약세 분석가가 토론하고, 공격적/중립/보수 리스크 분석가가 다시 검토한 뒤 최종 매수/보유/매도 판단
