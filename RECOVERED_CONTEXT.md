# 쭈꾸미 복구 요약

마지막 확인: 2026-05-22 KST

중요:
- 이 파일은 채팅방이 또 멈추거나 사라졌을 때 후임 Codex/사람이 그대로 이어가기 위한 인수인계 문서다.
- 쭈꾸미 관련 중요한 결정, 주소, 명령어, 현재 상태는 앞으로 이 파일 또는 `CURRENT_STATE.md`에 반드시 남긴다.
- 사용자는 초보자 기준으로 작업한다. 설명은 짧고, 명령어는 한 줄씩, 원인과 조치는 먼저 간단히 쓴다.

이 파일은 이전 채팅방이 context_length_exceeded 오류로 멈췄을 때, 새 채팅에서 바로 이어가기 위한 복구 요약이다.

## 현재 결론

- 이전 채팅 자체를 자동으로 통째로 가져올 수는 없다.
- 대신 로컬 파일, Git 원격, Render 설정, 실행 로그 기준으로 현재 상태를 재구성했다.
- 이 채팅에서 쭈꾸미 작업을 이어가면 된다.
- 앞으로 새 채팅에서 시작할 때는 먼저 이 파일을 읽고 시작한다.

## 2026-05-25 전략 보완

- 문제: 윈도우 Codex 모의매매가 `P라인 바닥` 중심이라 신호가 너무 적었다.
- 사용자 관찰: 피봇라인에 닿지 않아도 상승/하락이 멈추고, 봉이 짧아지고, 둥글게 라운딩하면 직전 진행 방향의 반대 매매를 시도할 수 있다.
- 코드 반영:
  - `market_reason_mvp/market_signal_bot.py`
  - 새 후보 `라운딩 바닥 롱`, `라운딩 천장 숏` 추가.
  - 피봇/주요 지지저항 터치를 필수로 하지 않는다.
  - 확인봉, 손절, 익절, 무효 조건은 유지한다.
- 모의매매 반영:
  - `market_reason_mvp/paper_signal_runner.py`
  - 기본 `--setup-contains`를 `P라인 바닥`에서 `라운딩`으로 변경했다.
  - 기본 `--min-level`을 4에서 2로 낮췄다.
  - 이유: 라운딩은 아직 강한 후보만 보는 단계가 아니라, 대기 후보까지 실제 결과를 기록해야 한다.
- 주의:
  - 아직 Render 재개/텔레그램 자동 발송 기준이 아니다.
  - 먼저 드라이런과 윈도우 모의매매로 검증한다.
  - 아직 GitHub 업로드용 폴더 `_보관/us100_render_upload`에는 반영하지 않았다.
  - 검증 후 배포하기로 결정하면, 그때 업로드용 Git 폴더에 동기화하고 `27yooon/us100-market-volatility-bot`에만 push한다.

## 2026-05-27 운영 방향 변경

- 오늘 이후 윈도우 Codex/윈도우 PC 모의매매는 사용하지 않는다.
- 앞으로 쭈꾸미 진행은 이 맥 Codex 기준으로 한다.
- 윈도우와 GitHub로 결과를 주고받는 자동화는 우선순위에서 제외한다.
- 다음 목표는 이 맥에서 라운딩 기준을 실시간 모의매매로 새로 검증하고, 통과하면 GitHub/Render 배포 준비를 하는 것이다.

## 2026-05-28 맥 모의매매 준비

- 맥 실행 안내: `MAC_PAPER_RUN.md`
- 첫날 새로 시작: `reset_and_run_paper_mac.command`
- 다음날부터 이어서 실행: `run_paper_mac.command`
- 기본 종료 시간이 다음 `02:00 KST`로 바뀌었다.
- 두 실행 파일은 `caffeinate`를 사용해서 실행 중 맥 잠자기를 막는다.
- 로그는 `market_reason_mvp/logs/paper_runner_live.log`에 저장한다.
- 검증 시간은 매일 `22:00~02:00 KST`.
- 1차 검증은 `2026-06-12`까지 또는 실시간 모의매매 10회 이상 쌓이면 판단한다.

## 2026-05-28 일봉 피봇 보완

- 사용자 피드백: 라운딩뿐 아니라 일봉상 피봇도 봐야 한다.
- 코드 반영:
  - `market_reason_mvp/market_signal_bot.py`
  - `daily_pivot_context()` 추가.
  - 라운딩 후보가 일봉 `P / R1 / R2 / S1 / S2`와 맞는지 확인한다.
  - 피봇 근처와 방향이 맞으면 근거를 추가한다.
  - 피봇과 멀거나 일봉 P 기준 방향이 안 맞으면 주의를 추가해서 레벨을 낮춘다.
- 점검 결과:
  - 2026-05-27 라운딩 숏 3개는 기존 `LEVEL 2`였지만, 보완 후 `LEVEL 1`로 내려가 `LEVEL 2+` 모의매매에서는 제외된다.

## 2026-05-29 P라인 반등 롱 추가

- 사용자 피드백: P라인 근접 후 다시 상승한 자리는 들어갈 수 있었다.
- 코드 반영:
  - `market_reason_mvp/market_signal_bot.py`
  - `P라인 반등 롱 확인` 추가.
  - 일봉 P라인 근접 후, P 아래 확정 이탈 없이 다시 회복하는 빠른 롱 자리다.
  - 기존 `P라인 바닥 횡보 롱`보다 빠르게 잡는다.
- 모의매매 반영:
  - `market_reason_mvp/paper_signal_runner.py`
  - 기본 필터를 `라운딩`에서 `라운딩,P라인`으로 변경했다.
- 문서:
  - `TRADING_METHODS.md`에 현재 매매법 전체를 정리했다.
- 점검 결과:
  - 2026-05-28 KST 후행 평가에서 `P라인 반등 롱 확인`은 4회, 3승 1패.
  - 사용자가 지적한 2026-05-28 23:45 KST 자리는 새 로직에서 `LONG LEVEL 2`, 후행 `WIN +50pt`로 잡힌다.

## 새 Codex가 가장 먼저 해야 할 일

1. 이 파일을 읽는다.
2. `CURRENT_STATE.md`를 읽는다.
3. `BOT_ROOM_SUMMARY.md`를 읽는다.
4. 사용자가 윈도우 Codex 모의매매 결과를 가져왔는지 확인한다.
5. 절대 `autotrade_mvp/.env` 내용을 출력하지 않는다.
6. Render/GitHub에서 삭제, 결제, 배포 전에는 반드시 `쭈꾸미` 프로젝트인지 확인한다.

## 프로젝트

- 이름: 쭈꾸미
- 목적: US100 / NDX / NQ=F 트레이딩 보조
- 핵심:
  - TradingView/Pine 신호기
  - 텔레그램 알림 봇
  - Render Cron Job 배포
  - 시장 변동, 뉴스, 지표 보조 알림

## 로컬 폴더

- 현재 작업 폴더:
  - `/Users/yooon/Desktop/쭈꾸미`
- GitHub/Render 업로드용 Git 폴더:
  - `/Users/yooon/Desktop/쭈꾸미/_보관/us100_render_upload`

주의:
- 현재 작업 폴더 루트는 Git 저장소가 아니다.
- Git 저장소는 `_보관/us100_render_upload` 안에 있다.
- 따라서 코드 수정은 보통 `/Users/yooon/Desktop/쭈꾸미`에서 먼저 하고, 검증 후 필요한 파일만 `_보관/us100_render_upload`에 반영해서 GitHub에 올리는 흐름이다.
- 폴더명이 한글이라 터미널에서 경로 문제가 생기면 절대경로를 따옴표로 감싼다.

예:

```bash
cd "/Users/yooon/Desktop/쭈꾸미"
```

## GitHub

- 저장소:
  - `https://github.com/27yooon/us100-market-volatility-bot.git`
- 브랜치:
  - `main`
- 마지막 확인 기준:
  - 로컬 `main`과 `origin/main`은 같은 커밋이다.
- 최근 커밋:
  - `ebfea49 Improve beginner signal alert formatting`
  - `51d0dbb Switch signal bot to levels and NQ futures`
  - `d363c42 Add market signal bot and cron deploy config`
  - `d3e32e2 Initial Render deploy setup`
- 2026-05-22 권한 확인:
  - 터미널 `git` 사용 가능: `/usr/bin/git`
  - GitHub 원격 읽기 가능: `git ls-remote origin main` 성공
  - GitHub push 권한 확인: `git push --dry-run origin main` 성공
  - 결과: 실제 변경 없이 `Everything up-to-date`
  - 따라서 이 맥에서는 터미널 Git 방식으로 push 가능하다.
- 2026-05-22 Chrome 확인:
  - Chrome에서 GitHub `https://github.com/settings/profile` 접속 시 로그인 계정은 `27yooon`.
  - 화면에 `27yooon (27yooon)` / `Your personal account`로 표시됨.
  - 쭈꾸미 GitHub 작업은 반드시 `27yooon` 계정 기준으로 진행한다.

주의:
- 최신 전략/평가 파일 중 일부는 현재 작업 폴더에만 있고 GitHub 업로드용 폴더에는 아직 없는 것으로 보인다.
- 특히 아래 파일은 현재 작업 폴더에만 있다.
  - `market_reason_mvp/paper_signal_runner.py`
  - `market_reason_mvp/signal_dryrun_evaluator.py`
  - `market_reason_mvp/TELEGRAM_PROMPT.md`
- 이 파일들은 현재 전략 검증에 중요하므로, GitHub 반영 전 누락 여부를 반드시 확인한다.
- `gh` 명령은 이 맥에서 설치되지 않은 상태였다. GitHub 확인은 `git remote -v`, `git fetch`, 브라우저, 또는 GitHub 앱/연결 도구로 한다.
- Codex GitHub 앱 상태:
  - 인증 사용자: `Inwest1997`
  - 설치 계정: `Inwest1997`, `KR-0822`
  - `27yooon/us100-market-volatility-bot`는 조회 가능하지만 권한은 `pull: true`, `push: false`.
  - 즉 Codex GitHub 앱 계정은 쭈꾸미 기준 계정이 아니다.
  - 하지만 Chrome GitHub 로그인은 `27yooon`이고, 로컬 Git 원격 push dry-run은 성공했다.
  - 쭈꾸미 저장소 반영은 현재 기준으로 터미널 Git 또는 Chrome의 27yooon 로그인 세션을 사용한다.

GitHub 업로드용 폴더 확인:

```bash
cd "/Users/yooon/Desktop/쭈꾸미/_보관/us100_render_upload"
git status --short --branch
git remote -v
```

## Render

- 서비스 방식:
  - 비용 때문에 Background Worker가 아니라 Cron Job
- Render 서비스 이름:
  - `us100-market-signal-bot`
- 현재 운영 판단:
  - 자동 텔레그램 발송은 재정비 전까지 재개하지 않는다.
  - Render Cron Job은 일시중지 상태로 보는 것이 현재 기준이다.
- 2026-05-22 Chrome 확인:
  - Render 대시보드 접속 가능: `https://dashboard.render.com`
  - 워크스페이스: `J's workspace`
  - 워크스페이스 URL 조각:
    - `tea-d801n650lvsc738a03h0`
  - 플랜: Hobby
  - 결제수단: 등록되어 있음
  - Billing 화면에서 이번 달 `Cron Jobs` 사용량이 표시됨.
  - Render 검색에서 서비스 발견:
    - 이름: `us100-market-signal-bot`
    - 프로젝트: `My project`
    - 환경: `Production`
    - 상태: `Suspended by you`
    - 서비스 URL:
      - `https://dashboard.render.com/cron/crn-d866d7p9rddc73f1op80`
- `render.yaml` 명령:
  - `python market_reason_mvp/market_signal_bot.py --once --symbol=NQ=F --min-level=3 --min-rr=1.30`
- 환경변수:
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`

주의:
- `.env`는 로컬에만 둔다.
- 토큰과 채팅 ID는 절대 채팅에 노출하지 않는다.
- Render에 토큰을 넣을 때도 코드나 문서에 쓰지 말고 Render 환경변수 화면에만 넣는다.
- Render에서 삭제/결제/배포 전에는 반드시 서비스 이름이 `us100-market-signal-bot`인지 확인한다.
- 현재 기준으로 자동 발송은 검증 전까지 켜지 않는다.
- Render 전용 CLI/API 권한은 확인되지 않았다.
- Render 작업은 현재 기준으로 Chrome 로그인 세션을 통해 처리해야 한다.
- Render 서비스는 삭제된 것이 아니라 검색으로 찾을 수 있다.
- 프로젝트 첫 화면에 `No active services`가 보여도, 검색창에서 `us100`을 검색하면 `us100-market-signal-bot`가 나온다.
- Chrome 자동화 환경은 아래처럼 정상 확인됐다.

## Telegram

2026-05-22 확인:

- 로컬 설정 파일:
  - `/Users/yooon/Desktop/쭈꾸미/autotrade_mvp/.env`
- `.env`에 아래 키가 설정되어 있다.
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`
- 값은 절대 출력하지 않는다.
- 현재 Telegram Bot API 확인 결과:
  - 설정 있음: `true`
  - Bot API 응답: `ok`
  - 봇 이름: `us100 signal bot`
  - 봇 username: `us100_yoon_bot`
  - 연결 채팅 타입: `private`
  - 연결 채팅 이름: `Yoon J`
- 확인 방식:
  - `/getMe`
  - `/getChat`
  - 테스트 메시지는 보내지 않았다.
- 과거 실제 전송 로그:
  - `market_reason_mvp/logs/market_reason_events.jsonl`
  - `telegram_ok: true` 기록 다수 있음.
  - 로그상 과거 봇 발신자도 `us100 signal bot` / `us100_yoon_bot`로 확인됨.
- 현재 판단:
  - 텔레그램 연동은 살아 있다.
  - Render 자동 발송이 멈춘 이유는 텔레그램 문제가 아니라, 매매 판단이 애매해서 `us100-market-signal-bot` Cron Job을 `Suspended by you` 상태로 둔 것이다.

주의:
- 텔레그램 토큰/채팅 ID는 채팅, 문서, GitHub에 절대 쓰지 않는다.
- 테스트 메시지를 보낼 때도 사용자의 허락을 받고 보낸다.

## Chrome / 브라우저 권한

2026-05-22 확인:

- Google Chrome 설치됨:
  - `/Applications/Google Chrome.app`
  - 버전 `148.0.7778.169`
- Chrome 실행 중:
  - `running: true`
- Codex Chrome Extension:
  - 설치됨: `true`
  - 활성화됨: `true`
  - 선택 프로필: `Default`
- Native Messaging Host:
  - 정상: `correct: true`
  - manifest:
    - `/Users/yooon/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.openai.codexextension.json`

의미:
- Codex가 Chrome을 조작할 수 있는 기본 환경은 준비되어 있다.
- GitHub, Render, TradingView 같은 로그인 사이트는 Chrome 세션이 로그인되어 있으면 대신 확인/조작할 수 있다.
- 다만 삭제, 결제, 배포, 서비스 중지/재개 같은 위험 작업은 실행 직전에 사용자에게 프로젝트 이름과 작업 내용을 확인받는다.

## 핵심 파일

- `market_reason_mvp/market_signal_bot.py`
  - 현재 메인 신호 봇
  - P라인 바닥 횡보 롱, 피보 눌림 롱, 피보 반등 숏, 상승 피로 숏, 하락 피로 롱 등이 들어 있다.
- `market_reason_mvp/paper_signal_runner.py`
  - 초보자 모의매매 기록기
  - 실제 주문 없음
  - 텔레그램 자동 발송 기본 없음
- `market_reason_mvp/signal_dryrun_evaluator.py`
  - 과거 신호 평가기
- `market_reason_mvp/TELEGRAM_PROMPT.md`
  - 텔레그램 메시지 형식 기준
- `render.yaml`
  - Render Cron Job 설정
- `autotrade_mvp/.env`
  - 로컬 텔레그램 토큰/채팅 ID
  - 절대 내용 출력 금지

## 현재 신호 전략

- 종목:
  - 기본 `NQ=F`
  - 이유: `^NDX`는 현물이라 장외 시간에 멈출 수 있음
- 기준 차트:
  - 5분봉
- 목표:
  - 하루 2~3회 정도 좋은 후보만
- 점수 기준:
  - 진입가 기준 +50포인트가 손절/무효보다 먼저 오면 WIN
- 자동 발송 재개 기준:
  - 최근 드라이런 10개 중 8개 이상 성공

## 현재 가장 중요한 패턴

- `P라인 바닥 횡보 롱`
- 의미:
  - P라인 터치 또는 근접
  - 저점 형성
  - 작은 봉으로 횡보
  - 더 이상 저점을 깨지 않음
  - 박스 상단 회복/돌파 후 롱 후보
- 현재 결론:
  - 빠른 스캘핑보다 3~4시간짜리 반등/지속 매매에 더 잘 맞는다.

## 최근 평가 결론

- 혼합 신호는 아직 자동 발송 기준 미달.
- 좋은 편:
  - `바닥 횡보 롱 확인`
  - `P라인 바닥 횡보 롱`
- 나쁜 편:
  - 강한 추세 중 `상승 피로 숏`
  - 강한 추세 중 `하락 피로 롱`
  - 일부 피보 반등/눌림 신호
- 결론:
  - 전체 신호를 보내면 안 된다.
  - 자동 발송 재개 시에도 `P라인 바닥 횡보 롱` 위주로 제한해야 한다.

## 현재 모의매매 상태

- 사용자가 정정함:
  - 현재 모의매매는 이 맥 Codex에서 진행 중이 아니다.
  - 윈도우 Codex에서 실행 중이다.
- 이 맥에 있는 상태 파일:
  - `market_reason_mvp/logs/paper_signal_state.json`
  - 이 파일은 로컬에 남은 참고 상태일 수 있으므로 현재 진행 상태로 단정하지 않는다.
- 현재 이 맥 채팅의 역할:
  - 코드 수정
  - 전략 정리
  - 결과 분석
  - GitHub/Render 반영 준비
- 윈도우 Codex 결과를 받을 때 확인할 파일:
  - `market_reason_mvp/logs/paper_signal_state.json`
  - `market_reason_mvp/logs/paper_trades.csv`
  - `market_reason_mvp/logs/paper_trades.jsonl`
  - 실행 로그 캡처 또는 `paper_runner_live.log`

윈도우 모의매매 해석 기준:
- 매매 횟수
- 승/패
- 총 포인트
- 매매당 평균 포인트
- 신호가 0회면 오류가 아니라 조건이 엄격했을 가능성이 크다.

## 방금 확인한 드라이런

명령:

```bash
python3 market_reason_mvp/market_signal_bot.py --once --dry-run
```

결과:

```text
❌ 지금 진입 금지
NQ=F 29609.50

지금 할 일: 아무것도 누르지 않기

이유: 상승 충격파 이후 / Fib 38.2 근처(29613.11)
주의: 없음

2026-05-22 17:46:36 KST
```

## 다음 작업 우선순위

1. 현재 작업 폴더의 최신 파일과 GitHub 업로드용 폴더 차이를 정리한다.
2. `WATCH`와 `ENTRY`를 코드/메시지에서 확실히 분리한다.
3. `P라인 바닥 횡보 롱`만 따로 평가한다.
4. 최근 10개 중 8개 이상 성공 전까지 Render 자동 발송은 재개하지 않는다.
5. 검증 통과 후에만 GitHub와 Render에 반영한다.

## 앞으로 반드시 기록할 것

작업이 끝날 때마다 아래를 이 파일 또는 `CURRENT_STATE.md`에 남긴다.

- 무엇을 바꿨는지
- 어떤 파일을 수정했는지
- 어떤 명령어로 테스트했는지
- 테스트 결과가 PASS인지 FAIL인지
- GitHub에 올렸는지
- Render에 반영했는지
- 자동 발송을 켰는지/껐는지
- 다음에 해야 할 일

## 절대 하지 말 것

- `.env` 내용 출력
- 텔레그램 토큰/채팅 ID 채팅에 붙여넣기
- 검증 전 Render 자동 발송 재개
- `LEVEL 3`을 바로 진입 신호처럼 표현
- GitHub/Render에서 프로젝트 이름 확인 없이 삭제/배포/결제
- 쭈꾸미와 관련 없는 이모저모 웹/앱 파일 정리

## 현재 사용자 요청

- 이전 채팅처럼 context 오류가 나면 진행 상황을 잃을 수 있으므로, 앞으로 모든 중요한 작업은 쭈꾸미 파일에 상세히 기록해야 한다.
- 후임자가 봐도 주소, 경로, 상태, 다음 행동을 알 수 있게 적는다.
- 사용자는 “또 뻑나면 못한다”고 했으므로, 채팅 기억에만 의존하지 않는다.
