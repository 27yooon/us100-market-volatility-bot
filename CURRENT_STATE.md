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

## 노션 자동기록

- 2026-06-01 KST 결정 및 정정:
  - 자동기록은 필요하다.
  - Render에서 도는 두 가지 모의매매 결과를 사람이 보기 쉬운 거래 일지 형태로 노션에 남긴다.
  - 우선 텔레그램은 쓰지 않고, 노션은 상태/거래/근거 기록용으로 사용한다.
  - 절대로 Codex/ChatGPT에 연결된 Notion MCP 또는 노션 커넥터에 기록하지 않는다.
  - 노션 기록은 사용자가 연결해둔 쭈꾸미 프로젝트용 Notion API로만 한다.
- 잘못 생성한 Codex 연결 노션 DB:
  - 이름: `쭈꾸미 모의매매 기록`
  - 조치: 2026-06-01 KST 즉시 휴지통 처리.
  - 앞으로 사용 금지.
- 사용자 Notion API:
  - 현재 프로젝트 파일에서 Notion API 코드/환경변수 흔적은 아직 확인되지 않았다.
  - 사용자가 확인용으로 준 Notion/API 기준 후보 주소:
    - `https://app.notion.com/p/code_hub-33af6018754380bcb4c2ed88103d6cae?source=copy_link`
  - 위 주소가 실제 데이터베이스인지, API 연결 안내 페이지인지, 또는 DB를 포함한 허브 페이지인지는 아직 확인 전이다.
  - 필요한 Render 환경변수 예시 이름: `NOTION_API_TOKEN`, `NOTION_DATABASE_ID`
  - 토큰값은 파일, GitHub, 채팅에 노출하지 않는다.
  - Render 환경변수로만 넣는다.
- 기록 컬럼:
  - `Time`: 기록 시간
  - `Strategy`: `zukkumi_rules` 또는 `public_indicator_rules`
  - `Event`: `START`, `HEARTBEAT`, `OPEN`, `CLOSE`, `ERROR`
  - `Symbol`, `Price`, `Side`, `Setup`, `Entry`, `Stop`, `Target`
  - `Result`, `PnL`, `Trades`, `Wins`, `Losses`, `Open Position`
  - `Reasons`, `Notes`, `Render URL`
- 첫 샘플 기록:
  - `2026-06-01 22:44 KST HEARTBEAT zukkumi_rules`
  - `2026-06-01 22:44 KST HEARTBEAT public_indicator_rules`
  - 당시 가격: `NQ=F 30410.25`
  - 두 전략 모두 매매 0회, 열린 포지션 없음.
  - 주의: 이 샘플은 잘못된 Codex 연결 노션에 만들어졌다가 DB와 함께 휴지통 처리했다.
- 운영 방식:
  - 1단계: 프로젝트 Notion API 연결 정보를 확인한다.
  - 2단계: Render Worker가 Notion API 토큰과 DB ID를 env로 받아 `OPEN/CLOSE/HEARTBEAT`를 직접 기록하게 만든다.
  - 3단계: Codex는 Render 로그와 노션 기록이 일치하는지만 확인한다.
- 2026-06-01 샘플 파일:
  - `NOTION_TRADE_LOG_SAMPLE.md`: 노션 DB 구조와 샘플 행 설명.
  - `notion_trade_log_sample.csv`: 노션으로 가져갈 수 있는 CSV 샘플.
  - 이 파일들은 사용자가 직접 원하는 Notion 위치로 옮기기 위한 임시본이다.
- 2026-06-02 템플릿 보강:
  - 기존 노션 샘플이 너무 성의 없다는 사용자 피드백을 받았다.
  - `NOTION_TRADE_LOG_SAMPLE.md`를 `쭈꾸미 모의매매 운영 대시보드 템플릿 v2`로 전면 교체했다.
  - `notion_trade_log_sample.csv`도 실제 거래/상태 기록용 컬럼으로 다시 만들었다.
  - 사용자 지정 Notion `code_hub` 페이지에 Chrome으로 직접 v2 템플릿을 붙여 넣었다.
  - Notion 위치: `https://app.notion.com/p/code_hub-33af6018754380bcb4c2ed88103d6cae`
  - Codex/ChatGPT Notion 커넥터는 사용하지 않았다.
- 2026-06-02 날짜별 보기 보강:
  - 사용자 피드백: "날짜별로 볼 수 있어야 되는 것 아니냐".
  - `NOTION_TRADE_LOG_SAMPLE.md`에 `날짜별 일지` 섹션을 추가했다.
  - `2026-06-02 화요일`, `2026-06-03 수요일` 구조로 일간 요약, 전략별 요약, 거래 상세, 복기를 보게 했다.
  - `notion_trade_log_sample.csv`에 `Date` 컬럼을 추가했다.
  - Notion `code_hub`에도 `쭈꾸미 날짜별 모의매매 보기 보강` 섹션을 Chrome으로 직접 추가했다.
  - 추천 Notion 보기: Daily Journal, Calendar, By Strategy, Open Positions, Wins/Losses, Review Needed.
- 2026-06-05 거래 목록형 v3 보강:
  - 사용자 피드백: "방금 정리한 것처럼 노션에도 정리하면 좋겠다".
  - `NOTION_TRADE_LOG_SAMPLE.md`를 전략별 거래 목록, 날짜별 보기, 복기 포인트 중심으로 수정했다.
  - `notion_trade_log_sample.csv`도 실제 Render 5개 거래 기준으로 다시 만들었다.
  - Notion `code_hub`에 `쭈꾸미 모의매매 거래 목록 v3` 섹션을 Chrome으로 직접 추가했다.
  - 포함 내용:
    - 전체 요약: `zukkumi_rules` 4회 2승 2패 +36.25pt, `public_indicator_rules` 1회 1승 +50pt
    - 전략별 거래 목록
    - 2026-06-02 / 2026-06-04 날짜별 거래 요약
    - 다음 확인: 2026-06-02 손실 2건 공통점, P라인 반등 롱 필터, 숏/라운딩 미체결 원인
  - Codex/ChatGPT Notion 커넥터는 사용하지 않았다.
- 2026-06-05 한눈에 보는 표 보강:
  - 사용자 스크린샷 기준으로 `# / 진입 시각 / 방향 / 셋업 / 진입가 / 청산 시각 / 결과 / 손익` 컬럼만 남긴 보기 좋은 표를 추가했다.
  - Notion `code_hub`에 `쭈꾸미 모의매매 한눈에 보는 표` 섹션을 Chrome으로 직접 추가했다.
  - `zukkumi_rules`와 `public_indicator_rules`를 분리해 표와 합계를 표시했다.
  - `NOTION_TRADE_LOG_SAMPLE.md`에도 같은 섹션을 추가했다.
- 2026-06-05 장기 Notion DB/API 구조 전환 준비:
  - 사용자 지적: 문서 표만으로는 필터링/누적/장기 운영이 안 된다.
  - 결론: 장기 운영은 Notion Database + Render Worker API append 방식이어야 한다.
  - 새 파일: `NOTION_DATABASE_SETUP.md`
  - 새 코드: `market_reason_mvp/notion_trade_logger.py`
  - 수정 코드: `market_reason_mvp/render_dual_paper_worker.py`
  - 동작:
    - Render 환경변수 `NOTION_API_TOKEN`, `NOTION_DATABASE_ID`가 있으면 START/HEARTBEAT/OPEN/CLOSE/ERROR를 Notion DB에 자동 추가한다.
    - 환경변수가 없으면 기존처럼 Render 로그만 남긴다.
  - 검증:
    - `python3 -m py_compile market_reason_mvp/notion_trade_logger.py market_reason_mvp/render_dual_paper_worker.py` 통과.
  - 아직 하지 않은 것:
    - 사용자 Notion에 실제 Database 생성
    - Render 환경변수 2개 설정
    - GitHub push 및 Render redeploy
  - 주의: Notion 토큰은 절대 파일/GitHub/채팅에 적지 않는다.
- 2026-06-05 Notion 사용 구조 재정리:
  - 사용자 피드백: "아직도 한 뭉텅이고, 어떻게 사용할지 모르겠다."
  - 결론: 한 페이지에 표를 계속 붙이는 방식은 폐기하고, 3개 DB로 나눠야 한다.
  - 새 파일:
    - `notion_trades_db.csv`: 모든 거래 원본 DB
    - `notion_daily_summary_db.csv`: 날짜별 일간 요약 DB
    - `notion_review_queue_db.csv`: 손실/문제 복기 DB
    - `NOTION_USE_GUIDE.md`: 매일 보는 순서와 DB 사용법
  - Notion `code_hub`에 `쭈꾸미 Notion은 이렇게 써야 함` 섹션을 Chrome으로 직접 추가했다.
  - 앞으로 사용 구조:
    1. 일간 요약 DB 먼저 확인
    2. 손실일이면 복기 DB 확인
    3. 세부 거래는 거래 DB에서 날짜/전략으로 필터
    4. Render 로그는 문제 확인용
    5. 자동기록 연결 후에는 손으로 표를 붙이지 않음
- 2026-06-05 사용자 신규 Notion DB 반영:
  - 사용자가 새 Notion DB를 만들었다.
  - URL: `https://app.notion.com/p/376f601875438194affcfc8613fc71a3?v=376f6018754381a0bd33000ce1db594d`
  - 제목: `매매일지`
  - Chrome으로 직접 열어 실제 Notion DB임을 확인했다.
  - Codex/ChatGPT Notion 커넥터는 사용하지 않았다.
  - 기존 샘플 행은 삭제하지 않았다.
  - 아래 실제 Render 거래 5건을 DB 행으로 추가했다:
    1. `2026-06-01 23:54 zukkumi LONG WIN`
    2. `2026-06-02 16:06 zukkumi LONG LOSS`
    3. `2026-06-02 20:47 zukkumi LONG LOSS`
    4. `2026-06-04 02:46 zukkumi LONG WIN`
    5. `2026-06-04 14:17 public LONG WIN`
  - 확인한 컬럼:
    - 매매명
    - 1차 익절가
    - R배수
    - 결과
    - 계약수
    - 날짜
    - 복기
    - 손익(pt)
    - 전략
    - 종목
    - 진입가
    - 차트 링크
    - 청산가
    - 포지션
  - 2026-06-06 Notion 표 보강:
    - 사용자 피드백: 두 매매법이 한 표에 섞여 있어 바로 구분하기 어렵다.
    - Chrome으로 직접 `매매명` 오른쪽, `1차 익절가` 왼쪽에 `매매법 구분` 컬럼을 새로 만들었다.
    - 값 기준:
      - `쭈꾸미 룰`: 우리 피드백 기반 매매법. P라인 반등, P라인 바닥 횡보, 라운딩, EMA 흐름, 일봉 피봇을 보는 전략.
      - `공개지표 룰`: 외부 공개 사례를 참고해 단순화한 기술지표형 전략. EMA20/50, RSI14, Bollinger, ATR 기반.
    - 현재 입력값:
      - 샘플 행: `쭈꾸미 룰`
      - `2026-06-01 23:54 zukkumi LONG WIN`: `쭈꾸미 룰`
      - `2026-06-02 16:06 zukkumi LONG LOSS`: `쭈꾸미 룰`
      - `2026-06-02 20:47 zukkumi LONG LOSS`: `쭈꾸미 룰`
      - `2026-06-04 02:46 zukkumi LONG WIN`: `쭈꾸미 룰`
      - `2026-06-04 14:17 public LONG WIN`: `공개지표 룰`
    - 기존 `전략` 컬럼은 유지한다. `매매법 구분`은 표 앞쪽에서 보기 좋게 구분하기 위한 사람용 컬럼이다.
  - 2026-06-06 Notion 표 추가 정리:
    - 사용자 요청: `매매명`은 복잡한 전략명까지 넣지 말고 `날짜 시간 포지션`만 보이게 단순화한다.
    - 실제 거래 5건의 `매매명`을 다음 형식으로 수정했다:
      - `2026-06-04 14:17 LONG`
      - `2026-06-04 02:46 LONG`
      - `2026-06-01 23:54 LONG`
      - `2026-06-02 20:47 LONG`
      - `2026-06-02 16:06 LONG`
    - 표 정렬은 `날짜` 기준 `내림차순`으로 설정했다. 최신 날짜가 위에 온다.
    - `연도`, `월` 컬럼을 `매매법 구분` 오른쪽에 추가했다.
    - 현재 모든 샘플/거래 행에 `연도=2026`, `월=2026-06` 값을 채웠다.
    - 사용 방식:
      - 최신순 확인: 기본 표 그대로 본다.
      - 연도별 확인: `연도` 컬럼에서 필터/그룹화한다.
      - 월별 확인: `월` 컬럼에서 필터/그룹화한다.
      - 전략별 확인: `매매법 구분` 컬럼에서 필터/그룹화한다.
  - 2026-06-06 Notion 화면 정리:
    - 사용자 확인: `연도`, `월`은 화면용이 아니라 필터/그룹화용 보조 컬럼이다.
    - Chrome으로 직접 `연도`, `월` 컬럼을 기본 표에서 숨겼다.
    - 숨긴 컬럼은 삭제한 것이 아니며, Notion 필터/그룹에서는 계속 사용할 수 있다.
    - 기본 표 앞쪽 노출 순서: `매매명` -> `매매법 구분` -> `결과` -> `1차 익절가` -> `2차 익절가`.

## Render 24시간 감시 체크

- 2026-06-06 Render 비용 확인:
  - 확인 위치: Render Dashboard > Billing > Unbilled Charges
  - 현재 플랜: Hobby
  - 이번 달 현재까지 미청구 비용: `Services $1.08`
  - 비용 발생 서비스: `us100-dual-paper-worker`
  - Cron Jobs 비용: 화면상 `0.00`
  - 참고: 이는 Render 대시보드에 표시된 month-to-date 미청구 금액이며, 최종 청구 시점에는 실행 시간이 늘면 증가할 수 있다.
- 2026-06-02 09:05 KST heartbeat 확인:
  - Render 서비스: `us100-dual-paper-worker`
  - URL: `https://dashboard.render.com/worker/srv-d8eomv6k1jcs73a6vro0/logs`
  - 상태: 실행 중, 최신 HEARTBEAT 확인.
  - 최신 로그: `2026-06-02 09:05:36 KST HEARTBEAT`
  - 가격: `NQ=F 30458.75`
  - `zukkumi_rules`: trades 1, wins 1, losses 0, pnl_points +50.0, open false
  - `public_indicator_rules`: trades 0, wins 0, losses 0, pnl_points 0, open false
  - 로컬 맥 보조 감시: screen 없음, `paper_signal_runner/caffeinate` 프로세스 없음.
  - 현재 기준 운영은 Render이며, 로컬 맥 감시는 꺼져 있는 것이 정상.
  - Notion 기록: 사용자 Notion API 연결 전까지 자동기록 보류. Codex/ChatGPT 노션 커넥터 사용 금지.
- 2026-06-02 09:20 KST heartbeat 확인:
  - Render 상태: 실행 중, 최신 HEARTBEAT 확인.
  - 최신 로그: `2026-06-02 09:20:38 KST HEARTBEAT`
  - 가격: `NQ=F 30426.5`
  - `zukkumi_rules`: trades 1, wins 1, losses 0, pnl_points +50.0, open false
  - `public_indicator_rules`: trades 0, wins 0, losses 0, pnl_points 0, open false
  - 로컬 맥 보조 감시: screen 없음, `paper_signal_runner/caffeinate` 프로세스 없음.
  - 이전 확인 대비 새 매매 없음. Notion 기록은 사용자 Notion API 연결 전까지 보류.
- 2026-06-02 15:46 KST heartbeat 확인:
  - Render 상태: 실행 중, 최신 HEARTBEAT 확인.
  - 최신 로그: `2026-06-02 15:46:29 KST HEARTBEAT`
  - 가격: `NQ=F 30501.0`
  - `zukkumi_rules`: trades 1, wins 1, losses 0, pnl_points +50.0, open false
  - `public_indicator_rules`: trades 0, wins 0, losses 0, pnl_points 0, open false
  - 로컬 맥 보조 감시: screen 없음, `paper_signal_runner/caffeinate` 프로세스 없음.
  - 이전 확인 대비 새 매매 없음. Notion 기록은 사용자 Notion API 연결 전까지 보류.
- 2026-06-05 17:11 KST heartbeat 확인:
  - Render 상태: 실행 중, 최신 HEARTBEAT 확인.
  - 최신 로그: `2026-06-05 17:11:31 KST HEARTBEAT`
  - 가격: `NQ=F 30149.0`
  - `zukkumi_rules`: trades 4, wins 2, losses 2, pnl_points +36.25, open false
  - `public_indicator_rules`: trades 1, wins 1, losses 0, pnl_points +50.0, open false
  - 로컬 맥 보조 감시: screen 없음, `paper_signal_runner/caffeinate` 프로세스 없음.
  - 이전 2026-06-02 확인 대비 새 매매가 발생했다.
  - Render 24시간 화면에서 `OPEN/CLOSE` 상세 원문 검색은 잡히지 않았다. 상세 진입/청산 시간과 방향은 별도 로그 접근 또는 코드 보강 필요.
  - Notion 기록은 사용자 Notion API 연결 전까지 자동기록 보류. Codex/ChatGPT Notion 커넥터 사용 금지.
- 2026-06-05 23:12 KST heartbeat 확인:
  - Render 상태: 실행 중, 최신 HEARTBEAT 확인.
  - 최신 로그: `2026-06-05 23:12:18 KST HEARTBEAT`
  - 가격: `NQ=F 29799.75`
  - `zukkumi_rules`: trades 4, wins 2, losses 2, pnl_points +36.25, open false
  - `public_indicator_rules`: trades 1, wins 1, losses 0, pnl_points +50.0, open false
  - 로컬 맥 보조 감시: screen 없음, `paper_signal_runner/caffeinate` 프로세스 없음.
  - 이전 확인 대비 새 매매 없음.
  - Notion 기록은 사용자 Notion API 연결 전까지 자동기록 보류.
- 2026-06-05 상세 OPEN/CLOSE 재확인:
  - Render 로그 기간을 7일로 넓혀 `OPEN/CLOSE` 상세 원문을 확인했다.
  - `zukkumi_rules` 거래 4회:
    1. LONG, `P라인 반등 롱 확인`, opened_at `2026-06-01 23:54:25 KST`, entry `30432.25`, target `30482.25`, result WIN `+50.0`, closed_at `2026-06-02 00:20:00 KST`
    2. LONG, `P라인 반등 롱 확인`, opened_at `2026-06-02 16:06:31 KST`, entry `30537.25`, stop `30506.91`, result LOSS `-30.5`, closed_at `2026-06-02 20:00:00 KST`
    3. LONG, `P라인 반등 롱 확인`, opened_at `2026-06-02 20:47:04 KST`, entry `30548.5`, stop `30520.37`, result LOSS `-33.25`, closed_at `2026-06-02 22:05:00 KST`
    4. LONG, `P라인 반등 롱 확인`, opened_at `2026-06-04 02:46:11 KST`, entry `30614.75`, target `30664.75`, result WIN `+50.0`, closed_at `2026-06-04 03:25:00 KST`
	  - `public_indicator_rules` 거래 1회:
	    1. LONG, `공개기술지표 반등 롱`, opened_at `2026-06-04 14:17:42 KST`, entry `30481.5`, target `30531.5`, result WIN `+50.0`, closed_at `2026-06-04 15:50:00 KST`
	  - 현재까지 확인된 모든 거래는 `LONG`이었다.
	- 2026-06-06 왜 LONG만 들어갔는지 코드 기준 분석:
	  - Render 모의매매 엔진 자체는 LONG/SHORT 둘 다 처리한다. SHORT이면 목표가는 `entry - 50`, 손절은 `5분봉 종가가 stop 위로 마감` 기준으로 처리된다.
	  - `public_indicator_rules`에도 SHORT 조건은 있다. 조건은 Bollinger 상단 터치, EMA20 이탈, RSI14 > 52, EMA20 <= EMA50, 손익비 통과다.
	  - 하지만 실제 5건은 모두 LONG이었다. 이유는 통과한 신호가 전부 `P라인 반등 롱 확인` 또는 `공개기술지표 반등 롱`이었기 때문이다.
	  - 현재 쭈꾸미 규칙은 `P라인 근접 후 회복`, `P라인 아래 확정 이탈 실패`, `회복봉 고가 돌파` 같은 LONG 반등 구조를 강하게 잡는다.
	  - 반대로 사용자가 차트에서 지적한 `P라인 회복 실패`, `횡보 하단 이탈`, `EMA 아래 재차 밀림` 같은 SHORT 구조는 아직 `P라인 저항/이탈 숏`으로 독립 구현되어 있지 않다.
	  - 즉 문제는 숏이 불가능한 것이 아니라, 현재 P라인 규칙이 LONG 반등 쪽으로 치우쳐 있고 P라인 실패 숏을 같은 수준으로 후보화하지 못하는 것이다.
	  - 다음 보완 후보: `P라인 저항/이탈 숏` 추가. 기준은 P라인 위 회복 실패, 낮아지는 고점, EMA20/50 아래 흐름, 박스 하단 또는 P라인 재이탈, 무효 기준은 P라인/직전 박스 고점 위 5분봉 마감.
	- 2026-06-06 P라인 숏 대칭 로직 추가:
	  - 사용자 지적: "하락 후 반등해서 라인을 깨지 못하면 롱 반등과 같은 구조로 숏 진입해야 하는 것 아니냐."
	  - 반영 파일: `market_reason_mvp/market_signal_bot.py`
	  - 새 함수: `detect_pivot_rejection_short`
	  - 새 직접 확인 함수: `build_pivot_rejection_confirmed`
	  - 새 셋업명:
	    - 원시 후보: `P라인 저항 숏`
	    - 확인 후보: `P라인 저항 숏 확인`
	  - 기준:
	    - 일봉 P라인 근처까지 반등
	    - P라인 위 5분봉 확정 돌파 실패
	    - 마지막 봉이 P라인 아래로 다시 밀림
	    - EMA20 위로 과하게 회복하지 않음
	    - 손절은 P라인/반등 고점 위, 목표는 `entry - 50pt`
	  - `confirm_candidate`에도 SHORT P라인 후보는 확인 후 `entry - 50pt`를 1차 목표로 쓰도록 반영했다.
	  - 검증: `python3 -m py_compile market_reason_mvp/market_signal_bot.py market_reason_mvp/render_dual_paper_worker.py` 통과.
	- 2026-06-07 개선 패치:
	  - 목적: 실제 진입 거래만 쌓는 구조에서 벗어나, `미진입 후보`도 자동으로 기록하고 후행 평가한다.
	  - 반영 파일:
	    - `market_reason_mvp/render_dual_paper_worker.py`
	    - `market_reason_mvp/notion_trade_logger.py`
	  - 새 이벤트:
	    - `CANDIDATE_OPEN`: 기준은 보였지만 실제 진입하지 않은 후보.
	    - `CANDIDATE_CLOSE`: 후보가 이후 +50pt를 먼저 갔는지, 무효 기준을 먼저 맞았는지 후행 평가.
	  - 후보 후행 결과:
	    - `MISSED_ENTRY`: 안 들어갔는데 +50pt 목표를 먼저 달성한 후보. 놓친 진입 후보.
	    - `FILTERED_OK`: 무효 기준이 먼저 맞아 안 들어간 게 맞았던 후보.
	    - `AMBIGUOUS`: 같은 5분봉 안에서 목표와 무효가 같이 보여 수동 복기 필요.
	  - HEARTBEAT 요약에 추가된 값:
	    - `candidate_open`
	    - `missed_entries`
	    - `filtered_ok`
	  - Notion API logger에도 후보 상태/결과/필터 이유/복기 요약 필드를 추가했다.
	  - 검증:
	    - `python3 -m py_compile market_reason_mvp/render_dual_paper_worker.py market_reason_mvp/notion_trade_logger.py market_reason_mvp/market_signal_bot.py` 통과.
	    - `python3 market_reason_mvp/render_dual_paper_worker.py --once --symbol=NQ=F --poll=300` 통과.
	  - 주의:
	    - Notion 자동기록은 여전히 Render 환경변수 `NOTION_API_TOKEN`, `NOTION_DATABASE_ID`가 설정된 경우에만 동작한다.
	    - Codex/ChatGPT Notion 커넥터는 사용하지 않는다.
	- 2026-06-07 후보 기준 확장 패치:
	  - 사용자 지적: 하루에 실제 거래가 0회면 데이터가 쌓이지 않으므로, 진입 기준과 후보 기록 기준을 분리해야 한다.
	  - 반영 파일:
	    - `market_reason_mvp/render_dual_paper_worker.py`
	    - `market_reason_mvp/notion_trade_logger.py`
	  - 실제 모의 진입 기준은 기존처럼 엄격하게 유지한다.
	  - 새 관찰 후보:
	    - `P라인 관찰 롱`: P라인 근처에서 저점/회복 후보가 보이는 자리.
	    - `P라인 관찰 숏`: P라인 근처에서 반등/저항 후보가 보이는 자리.
	    - `라운딩 관찰 롱`: 하락 후 봉 축소/횡보로 바닥 후보가 보이는 자리.
	    - `라운딩 관찰 숏`: 상승 후 봉 축소/횡보로 천장 후보가 보이는 자리.
	  - 관찰 후보는 실제 진입하지 않고 `CANDIDATE_OPEN`으로 기록한 뒤, 이후 +50pt와 무효 기준 중 어느 쪽이 먼저 나오는지 후행 평가한다.
	  - HEARTBEAT 요약에 `ambiguous`, `observations`를 추가했다.
	  - Notion API logger에도 `Observation Type`, 후보/관찰 요약 수치를 추가했다.
	  - 검증:
	    - 로컬/업로드용 모두 `python3 -m py_compile ...` 통과.
	    - 업로드용 `python3 market_reason_mvp/render_dual_paper_worker.py --once --reset --symbol=NQ=F --poll=300` 통과.
	  - 현재 테스트 시점 가격 `NQ=F 29026.5`에서는 관찰 후보 0개였다. 이는 실행 오류가 아니라 현재 가격이 P라인/라운딩 관찰 조건에 걸리지 않았다는 의미다.
	- 2026-06-07 프리장 라인 미터치 라운딩 보강:
	  - 사용자 피드백: 굳이 라인에 닿지 않아도 봉이 짧아지고 라운딩하는 구간은 들어가볼 필요가 있으며, 특히 프리장에서 중요하다.
	  - 반영 파일: `market_reason_mvp/render_dual_paper_worker.py`
	  - KST 기준 세션 라벨 추가:
	    - `US_PREMARKET`: 17:00~22:30
	    - `US_REGULAR`: 22:30~05:00
	    - `EUROPE_TO_US_PRE`: 15:00~17:00
	    - `OFF_HOURS`: 그 외
	  - 프리장(`US_PREMARKET`)에서는 라운딩 관찰 조건을 완화했다.
	    - 라인 미터치라도 하락/상승 후 봉 축소와 횡보가 보이면 `라운딩 관찰 롱/숏` 후보로 기록한다.
	    - 프리장에서는 직전 움직임 기준을 `ATR 1.0`에서 `ATR 0.7` 수준으로 완화한다.
	    - 박스/횡보 판단도 조금 넓게 허용한다.
	  - 모든 관찰 후보 이유에 `세션 US_PREMARKET` 같은 세션 라벨을 남긴다.
	  - 검증:
	    - 로컬/업로드용 `py_compile` 통과.
	    - 업로드용 `--once --reset` 실행 통과.
	  - 현재 테스트는 KST 14시대라 프리장 조건은 아직 실제로 발동하지 않았다.

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
- 안정화 변경:
  - 2026-06-01 22:44 KST Render Start Command에서 `--reset` 제거
  - 현재 실행 명령:
    - `python market_reason_mvp/render_dual_paper_worker.py --symbol=NQ=F --poll=300`
  - 최신 확인:
    - `2026-06-01 22:44:16 KST START`
    - `2026-06-01 22:44:17 KST HEARTBEAT`
    - 가격: `NQ=F 30410.25`
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
- 현재 상태: 중지함
- 중지 시각: 2026-06-01 22:45 KST 전후
- 중지 이유: Render Background Worker가 정상 실행되어 노트북 없이 감시하는 방식으로 전환
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
  - 이 섹션은 과거 로컬 임시 감시 기록이다.
  - 현재 실제 감시는 Render `us100-dual-paper-worker`가 담당한다.

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

## 외부 참고 사례: MultiStrategy-Trader-Pro

- 확인 시각: 2026-06-07 KST
- GitHub: https://github.com/mahmoud20138/MultiStrategy-Trader-Pro
- 성격: MetaTrader 5 기반 다전략 자동매매/대시보드 프로젝트. Gold, NAS100, US500, US30, BTC, ETH를 대상으로 여러 전략을 돌리고, 점수화, 리스크 관리, 백테스트, 거래 일지를 함께 다룬다.
- 쭈꾸미에 바로 참고할 핵심:
  - 단일 조건 진입이 아니라 `전략 신호 -> 점수화 -> 리스크 게이트 -> 기록` 순서로 처리한다.
  - 모든 신호에 `score`, `quality_tier`, `score_breakdown`, `strategy_id`를 붙여 장기 검증이 가능하게 한다.
  - 실제 진입뿐 아니라 막힌 신호도 왜 막혔는지 기록한다.
  - 전략별, 날짜별, 방향별 성과를 따로 볼 수 있게 한다.
- NAS100 전략:
  - `ORB`: 뉴욕장 시작 후 첫 30분 고가/저가를 박스로 잡고 돌파 방향으로 진입. VWAP와 거래량 확인을 사용한다.
  - `EMA Ribbon`: EMA 9/21/55 배열이 한 방향으로 정렬된 뒤 stochastic pullback cross가 나오면 진입한다.
  - `ICT Power of 3`: 횡보 축적, 위/아래 훑기, BOS/FVG 확인 후 반대 방향 진입. 정의가 복잡하므로 쭈꾸미에서는 초기에는 관찰 후보로만 두는 편이 안전하다.
  - `Gap Fill`: 장 시작 갭 크기에 따라 작은 갭은 메우기, 큰 갭은 추세 지속으로 본다.
  - `20/50 EMA Pullback`: 일봉 EMA20/50 추세와 H4 트리거를 보는 스윙 전략이라 5분봉 모의매매에는 직접 진입보다 상위 추세 필터로 참고한다.
- 쭈꾸미 적용 우선순위:
  1. `score_total`과 `score_breakdown`을 모든 실제 진입/미진입 후보에 기록한다.
  2. NY opening range, 즉 22:30~23:00 KST 박스의 돌파/실패/되돌림을 관찰 후보로 추가한다.
  3. `public_indicator_rules`를 단순 지표식에서 `score_indicator_rules`로 개선한다.
  4. 리스크 게이트는 실거래 전 단계에서만 강제하고, 현재 Render 모의매매에서는 우선 `blocked_reason`으로 남긴다.
- 주의:
  - 이 repo는 MT5/브로커/Windows 전제가 강해서 Render의 yfinance 기반 쭈꾸미에 그대로 붙이면 안 된다.
  - 쭈꾸미에는 매매법 복사보다 `점수화/기록/검증 구조`를 가져오는 것이 맞다.

## ORB 전략 첨부 방향

- 논의 시각: 2026-06-07 KST
- ORB 뜻: Opening Range Breakout. 미국 정규장 시작 직후 일정 시간의 고가/저가 박스를 잡고, 그 박스를 돌파하거나 돌파 실패하는 흐름을 매매 후보로 보는 방식.
- 쭈꾸미 적용 방식:
  - 처음부터 실제 진입 전략으로 넣지 않는다.
  - 먼저 `public_indicator_rules`와 별도의 `orb_observation_rules` 또는 `ny_open_range_rules`로 관찰 후보만 쌓는다.
  - 기준 시간은 NY 오픈 후 15분 또는 30분 박스다. 한국시간 기준으로 일반적으로 22:30~22:45 또는 22:30~23:00이며, 서머타임/비서머타임 변경은 별도 처리해야 한다.
  - 기록할 항목: 박스 상단, 박스 하단, 박스 폭, 돌파 방향, VWAP/EMA 위치, ATR 대비 박스 크기, 돌파 후 되돌림 여부, 결과.
  - 쭈꾸미 기존 P라인/라운딩 전략과 충돌시키지 않고, 같은 시간대에 별도 후보로 기록한다.
- 우선 관찰할 후보:
  - `ORB_LONG_BREAKOUT`: 박스 상단 돌파 후 유지
  - `ORB_SHORT_BREAKOUT`: 박스 하단 돌파 후 유지
  - `ORB_FAILED_LONG`: 상단 돌파 실패 후 박스 안으로 복귀, 숏 관찰
  - `ORB_FAILED_SHORT`: 하단 돌파 실패 후 박스 안으로 복귀, 롱 관찰
- 실제 진입 전 필요한 검증:
  - 최소 2주 이상 관찰
  - 롱/숏 각각 최소 10건 이상
  - 승률보다 먼저 `박스 폭`, `ATR`, `시간대`, `돌파 후 되돌림`별 결과를 본다.
  - 바로 들어가는 돌파형이 좋은지, 돌파 후 되돌림 확인형이 좋은지 분리해서 비교한다.

## GitHub/TradingView 참고 아이디어 적용 순서

- 논의 시각: 2026-06-07 KST
- 결론: 전략을 바로 많이 추가하지 않고, 먼저 기록/비교 체계를 고정한 뒤 ORB와 점수제 전략을 관찰 후보로 붙인다.
- 1단계: 전략 버전 기록
  - 모든 이벤트에 `strategy_version`을 붙인다.
  - 예: `zukkumi_v1`, `zukkumi_v2_pivot_short`, `zukkumi_v3_candidate_log`, `zukkumi_v4_premarket_rounding`, `ny_orb_v1_observation`, `score_indicator_v1`.
  - 이유: 룰이 자주 바뀌면 같은 `zukkumi_rules` 안에 서로 다른 조건의 결과가 섞여 검증이 불가능해진다.
- 2단계: NY 오픈 박스 기록
  - 22:30~23:00 KST 박스의 high, low, mid, width를 매일 기록한다.
  - 후보 유형: 상단 돌파 롱, 하단 이탈 숏, 상단 돌파 실패 숏, 하단 이탈 실패 롱, mid 재테스트.
  - 처음에는 실제 진입이 아니라 관찰 후보만 기록한다.
- 3단계: ATR 변동성 필터
  - 박스 폭이 ATR 대비 너무 작으면 돌파 신뢰도가 낮으므로 후보만 기록한다.
  - 박스 폭이 ATR 대비 너무 크거나 직전 장대봉이면 추격 금지 후보로 기록한다.
  - 실거래 전에는 `blocked_reason`으로 남기고, 모의매매 단계에서는 통계 비교용으로 보관한다.
- 4단계: 점수제 공개지표 전략
  - 기존 `public_indicator_rules`를 바로 삭제하지 않고, 새 전략 `score_indicator_rules`로 별도 추가한다.
  - 점수 항목: EMA 방향, Bollinger 위치, RSI, MACD, Stochastic, ATR, 시간대, 추격 여부.
  - 결과 기록: `score_total`, `score_breakdown`, `quality_tier`.
- 5단계: 자동 리포트
  - 전략별, 버전별, 롱/숏별, 시간대별, 요일별로 거래 수, 승률, 손익합, Profit Factor, Max Drawdown, 연속 손실을 집계한다.
  - 노션에는 개별 거래/후보를 쌓고, 코드에서는 요약 리포트를 생성한다.
- 적용 원칙:
  - 기존 `zukkumi_rules`의 실제 진입 로직은 갑자기 바꾸지 않는다.
  - 새 아이디어는 `observation`으로 최소 2주 쌓은 뒤 실제 진입 후보로 승격한다.
  - 우선 필요한 것은 자동매매 완성보다, 나중에 믿을 수 있는 데이터가 쌓이는 구조다.

## 쭈꾸미 오리지널 보존 + 업그레이드 관찰 전략 추가

- 작업 시각: 2026-06-07 KST
- 원칙:
  - `zukkumi_rules` 실제 진입 로직은 건드리지 않는다.
  - `public_indicator_rules` 실제 진입 로직도 기존 비교군으로 남긴다.
  - 업그레이드 아이디어는 별도 관찰 전략으로만 기록한다.
- 코드 변경:
  - 파일: `market_reason_mvp/render_dual_paper_worker.py`
  - 모든 전략 상태/이벤트에 `strategy_version`을 붙이도록 추가.
  - 새 관찰 전략 `ny_orb_observation_rules` 추가.
  - 새 관찰 전략 `score_indicator_rules` 추가.
- 전략 버전:
  - `zukkumi_rules`: `zukkumi_v4_premarket_rounding`
  - `public_indicator_rules`: `public_indicator_v1`
  - `ny_orb_observation_rules`: `ny_orb_v1_observation`
  - `score_indicator_rules`: `score_indicator_v1_observation`
- `ny_orb_observation_rules`:
  - 한국시간 22:30~23:00 NY 오픈 박스를 계산한다.
  - high, low, mid, width, ATR 대비 박스폭을 기록한다.
  - 상단 돌파 롱, 하단 이탈 숏, 상단 돌파 실패 숏, 하단 이탈 실패 롱, 중간값 재테스트를 관찰 후보로 남긴다.
  - 실제 진입은 하지 않는다.
- `score_indicator_rules`:
  - EMA20/50, EMA200, Bollinger 위치, RSI, MACD histogram, Stochastic, 세션, ATR/추격 필터를 점수화한다.
  - `score_total`, `score_breakdown`, `quality_tier`를 후보 이벤트에 기록한다.
  - 실제 진입은 하지 않는다.
- 테스트:
  - `python3 -m py_compile market_reason_mvp/render_dual_paper_worker.py market_reason_mvp/market_signal_bot.py market_reason_mvp/notion_trade_logger.py` 통과.
  - `python3 market_reason_mvp/render_dual_paper_worker.py --once --reset --symbol=NQ=F --poll=300` 통과.
  - 주말이라 최신 5분봉은 2026-06-06 05:59:59 KST 금요일 마감봉으로 잡힘.
  - 테스트에서 `score_indicator_rules` SHORT 관찰 후보 1건 생성됨. 실제 거래 아님.

## 전략 이름 재명명

- 작업 시각: 2026-06-07 KST
- 이유: 기존 이름 `zukkumi_rules`, `public_indicator_rules`, `ny_orb_observation_rules`, `score_indicator_rules`가 대화에서 헷갈려서, 실제로 들어가는 전략과 관찰만 하는 전략이 바로 보이도록 이름을 정리했다.
- 앞으로 대화에서 부를 이름:
  - `쭈꾸미 원본`: 우리가 직접 정한 P라인, 라운딩, 피봇, EMA 중심 실제 모의매매 기준.
  - `기본지표`: Bollinger, EMA, RSI, ATR 기반 기본 공개지표 비교군. 실제 모의매매 가능.
  - `오픈박스 매매`: NY 오픈 22:30~23:00 KST 박스/ORB 기준을 통과하면 실제 모의매매로 진입.
  - `점수제 관찰`: EMA, Bollinger, RSI, MACD, Stochastic, ATR을 점수화해 후보만 관찰. 실제 진입 안 함.
- 코드 내부 이름:
  - `쭈꾸미 원본` = `zukkumi_original`
  - `기본지표` = `indicator_basic`
  - `오픈박스 매매` = `orb_paper`
  - `점수제 관찰` = `score_watch`
- 전략 버전:
  - `zukkumi_original`: `zukkumi_original_v4`
  - `indicator_basic`: `indicator_basic_v1`
  - `orb_paper`: `orb_paper_v1`
  - `score_watch`: `score_watch_v1`
- 호환 처리:
  - Render 상태 파일에 예전 이름이 남아 있어도 새 이름으로 자동 이전하도록 `render_dual_paper_worker.py`에 마이그레이션을 넣었다.
  - Notion 요약 로거도 새 이름과 예전 이름을 모두 읽을 수 있게 수정했다.

## 오픈박스 매매 승격

- 작업 시각: 2026-06-07 KST
- 이유: 사용자가 오늘 상의한 ORB/NY 오픈박스 전략도 관찰만 하지 말고 기존 두 모의매매와 별도인 세 번째 모의매매로 넣자고 결정.
- 변경:
  - 기존 `오픈박스 관찰` / `orb_watch`를 `오픈박스 매매` / `orb_paper`로 승격.
  - 예전 상태명 `orb_watch`나 `ny_orb_observation_rules`가 Render state에 남아 있으면 `orb_paper`로 자동 이전.
- 실제 진입 기준:
  - 22:30~23:00 KST NY 오픈 박스가 형성된 뒤에만 본다.
  - 상단 돌파 롱, 하단 이탈 숏, 상단 돌파 실패 숏, 하단 이탈 실패 롱, 중간값 재테스트 중 하나가 발생해야 한다.
  - `score_total >= 70`
  - `level >= 2`
  - `rr >= min_rr` 기본값 1.30
- 기록:
  - 기준 미달 ORB는 계속 후보로 기록한다.
  - 기준 통과 ORB는 `OPEN` 이벤트로 실제 모의매매 진입한다.
  - 실거래 아님. Render 모의매매 검증용.

## Codex 팀장 방 운영법 적용

- 확인 시각: 2026-06-07 KST
- 참고 자료: https://github.com/citizendev9c/yt-assets/blob/main/ai-productivity/codex-thread-chat-26-06-06/README.md
- 핵심: 한 채팅방에 리서치, 코드, 배포, 복기, 노션, 백테스트를 전부 섞지 않고, 이 방을 `팀장 방`처럼 사용한다. 팀장 방은 전체 판단, 지시, 완료 보고 취합, 다음 결정만 담당한다.
- 쭈꾸미 적용 구조:
  - `팀장 방`: 사용자가 지금 대화하는 메인 방. 전체 결정, 우선순위, 이름 정리, 최종 승인.
  - `전략 연구 방`: 새 매매법, GitHub/TradingView 참고, 룰 설계.
  - `코드/Render 방`: `market_reason_mvp` 코드 수정, GitHub push, Render 배포 확인.
  - `복기/데이터 방`: 거래 결과, 미진입 후보, 놓친 자리, 시간대별 통계 분석.
  - `노션/기록 방`: Notion DB 구조, 거래일지 정리, 후임자용 문서화.
  - `백테스트/리포트 방`: 전략별 승률, 손익합, Profit Factor, Max Drawdown, 롱/숏/시간대별 성과 리포트.
- 운영 규칙:
  - 짧고 단순한 작업은 이 방에서 바로 처리한다.
  - 역할이 다른 작업, 오래 걸리는 작업, 나중에 다시 이어갈 작업은 별도 담당 방으로 나누는 것을 우선 검토한다.
  - 각 담당 방은 결론 먼저, 근거 나중, 다음 단계 1줄 형식으로 보고한다.
  - 팀장 방은 완료 보고를 취합한 뒤 다음 단계 진행 여부를 사용자에게 확인한다.
  - 결제, 삭제, 실거래, 외부 발송, 계정 변경은 반드시 사용자 확인 후 진행한다.
- 주의:
  - 현재 자동매매는 실거래가 아니라 Render 모의매매다.
  - Notion 기록은 사용자가 연결한 프로젝트 Notion API 방식만 사용한다. Codex/ChatGPT 노션 커넥터에 임의 기록 금지.
  - GitHub는 반드시 `27yooon/us100-market-volatility-bot`만 사용한다.

## 팀장 방 운영표 파일 추가

- 작업 시각: 2026-06-07 KST
- 사용자 요청: “그럼 너가 말한대로 한번 해보자”
- 적용:
  - `AGENTS.md`에 Codex 팀장 방 운영 규칙을 추가했다.
  - `TEAM_ROOMS.md`를 새로 만들었다.
- `TEAM_ROOMS.md` 내용:
  - 팀장 방 / 전략 연구 방 / 코드·Render 방 / 복기·데이터 방 / 노션·기록 방 / 백테스트·리포트 방 역할 표
  - 각 담당 방에 붙여넣을 시작 지시문
  - 결론 먼저, 근거 나중, 다음 단계 1줄 보고 규칙
  - 위험 작업 사용자 확인 규칙
- 사용 방식:
  - 사용자는 계속 이 메인 방에 말하면 된다.
  - Codex가 필요할 때만 담당 방 성격으로 작업을 나눠 정리한다.
  - 스레드 자동 생성 도구가 없으면 `TEAM_ROOMS.md`의 지시문을 복사해 새 방에 붙여넣는 방식으로 운영한다.

## 앱 전환 계획 반영

- 작업 시각: 2026-06-08 KST
- 사용자 요청: “만약 승률 80프로 이상 나오면 어플로 구상할 때 필요한 점을 다 반영”
- 새 문서:
  - `APP_PRODUCT_PLAN.md`
- 핵심 내용:
  - 앱 전환 조건: 전략별 실제 모의매매 30회 이상, 후보 50건 이상, 최소 2~4주 검증, 승률 80% 이상, Profit Factor/Max Drawdown/연속 손실 확인.
  - 앱 화면: 운영 대시보드, 전략별 화면, 거래 복기 화면, 후보/미진입 화면, 리스크 관리 화면, 알림 화면.
  - 데이터 구조: strategies, strategy_versions, signals, paper_trades, missed_candidates, daily_summaries, risk_events, server_heartbeats, reviews.
  - 안전장치: 하루/주간 손실 제한, 연속 손실 정지, 과변동/뉴스/데이터 오류/heartbeat 지연 시 진입 금지.
  - 전환 단계: Render 모의매매 -> 자동 리포트 -> 웹 대시보드 MVP -> 모바일 대응 -> 알림 앱 -> 소액 실거래 검토 -> 완전 자동화 검토.
- 중요한 원칙:
  - 승률만 보고 앱/실거래로 넘어가지 않는다.
  - 전략 버전별 결과를 섞지 않는다.
  - 앱의 핵심은 진입 버튼이 아니라 검증, 복기, 리스크 제어, 운영 감시다.

## 진입 균형 원칙 추가

- 작업 시각: 2026-06-08 KST
- 사용자 지적: “무조건 들어가는 게 아니라 근거도 있어야 하고, 근거 찾다가 한 번도 안 들어가는 일도 없어야 한다.”
- 반영 문서:
  - `APP_PRODUCT_PLAN.md`
- 원칙:
  - 쭈꾸미는 무조건 진입 봇이 아니다.
  - 하지만 필터가 너무 많아서 1주일 내내 실제 진입이 0회라면 좋은 전략이 아니라 과도한 조건일 수 있다.
  - 실제 모의매매 진입에는 `위치`, `방향`, `무효 기준`, `손익 구조`가 필수다.
  - EMA, RSI, MACD, Stochastic, ATR, 세션, 거래량 등은 선택 근거로 점수화하되, 모든 선택 근거를 필수 조건으로 만들지 않는다.
- 점검 기준:
  - 1주일 실제 진입 0회: 조건 과도 가능성 점검.
  - 후보는 많은데 진입 0회: 필터가 너무 강한지 점검.
  - 점수 높은 후보가 계속 `MISSED_ENTRY`: 관찰 전략을 실제 모의매매로 승격 검토.
  - 점수 낮은 후보가 자주 수익: 점수 기준 재조정.

## 오늘 매매 여부 확인 개선

- 작업 시각: 2026-06-08 KST
- 사용자 문제 제기: “진입 여부는 어디서 봐? 오늘 매매 했는지 안했는지 매번 너한테 물어봐야해?”
- 결론:
  - 매번 Codex에게 물어보는 구조는 불편하므로 Render 로그에서 바로 보이게 개선한다.
- 코드 변경:
  - 파일: `market_reason_mvp/render_dual_paper_worker.py`
  - HEARTBEAT JSON에 `today_status`를 추가한다.
  - HEARTBEAT마다 사람이 읽는 줄 `[TODAY_STATUS] YYYY-MM-DD 오늘 매매 없음/오늘 진입 N회 ...`을 추가 출력한다.
- 새 문서:
  - `TODAY_TRADE_STATUS.md`
- 확인 위치:
  - Render 로그: `https://dashboard.render.com/worker/srv-d8eomv6k1jcs73a6vro0/logs`
  - 로그에서 `[TODAY_STATUS]`를 찾는다.
- 의미:
  - `오늘 매매 없음`: 오늘 실제 모의매매 진입 없음.
  - `오늘 진입 N회`: 오늘 실제 모의매매 진입 있음.
  - `보유 N건`: 아직 청산되지 않은 모의 포지션 있음.
  - `손익 +Npt`: 오늘 청산 기준 손익.

## 텔레그램/노션 알림 운영 반영

- 작업 시각: 2026-06-08 KST
- 사용자 요청: “거래마다 텔레그램 보내고, 밤 11시에 오늘 거래 총 보고, 노션에도 그대로 기록”
- 반영 파일:
  - `market_reason_mvp/render_dual_paper_worker.py`
  - `market_reason_mvp/notion_trade_logger.py`
  - `NOTIFICATION_RUNBOOK.md`
- Telegram:
  - `OPEN`, `CLOSE` 발생 시 즉시 알림.
  - 대상 전략: `쭈꾸미 원본`, `기본지표`, `오픈박스 매매`.
  - `점수제 관찰`은 실제 진입이 아니므로 즉시 알림 제외.
  - 23:00 KST 중간 보고.
  - 06:10 KST 전날 밤 미국장 최종 보고.
  - 필요 env: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
  - 선택 env: `TELEGRAM_PAPER_NOTIFY=false`면 알림 중지.
- Notion:
  - 기존 프로젝트 Notion API/env 방식만 사용.
  - `DAILY_REPORT`도 Notion 기록 대상에 포함.
  - 필요 env: `NOTION_API_TOKEN`, `NOTION_DATABASE_ID`.
- 중복 방지:
  - 상태 파일 `daily_reports_sent`에 보낸 보고 키를 저장해 같은 날 같은 보고가 중복 발송되지 않게 한다.
- 주의:
  - 모든 알림은 실거래가 아니라 Render 모의매매 기준이다.

## 2026-06-08 매매 리뷰 확인 상태

- 확인 시각: 2026-06-09 KST
- 사용자 요청: “어제 리뷰 못받았는데”
- 대상 날짜:
  - 어제 = 2026-06-08 KST
- 현재 확인한 내용:
  - GitHub 배포 저장소는 `27yooon/us100-market-volatility-bot`이다.
  - 텔레그램/노션/일일 보고 기능은 커밋 `c4f5450 Add paper trade Telegram and daily reports`로 반영 및 push 완료 상태다.
  - 로컬 로그 `/Users/yooon/Desktop/쭈꾸미/market_reason_mvp/logs/render_dual_paper_events.jsonl`에는 2026-06-07 테스트 START/HEARTBEAT까지만 남아 있어 2026-06-08 실제 Render 거래 내역을 판단할 수 없다.
  - Chrome으로 Render 로그 URL `https://dashboard.render.com/worker/srv-d8eomv6k1jcs73a6vro0/logs`를 열었으나 로그인 화면으로 이동했다.
- 원인:
  - 실제 어제 매매/후보/일일보고 여부는 Render 서버 로그에만 있고, 현재 Codex Chrome 세션은 Render 로그인이 풀려 있어 원문 확인이 막혀 있다.
- 조치:
  - 사용자가 Render에 다시 로그인하면 Render 로그에서 `2026-06-08`, `[TODAY_STATUS]`, `OPEN`, `CLOSE`, `DAILY_REPORT`, `telegram_sent`, `telegram_skipped`를 검색해 어제 리뷰를 확정한다.
  - 만약 로그에 `telegram_skipped: not_configured_or_disabled`가 보이면 Render 환경변수 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_PAPER_NOTIFY`를 확인한다.
  - 만약 `c4f5450` 이후 로그 형식이 보이지 않으면 Render 자동배포가 최신 커밋으로 갱신됐는지 확인한다.

## 2026-06-08 Render 매매 리뷰 확정

- 확인 시각: 2026-06-09 KST
- Render 로그 확인 완료:
  - 서비스: `us100-dual-paper-worker`
  - URL: `https://dashboard.render.com/worker/srv-d8eomv6k1jcs73a6vro0/logs`
- 2026-06-08 실제 모의매매 요약:
  - 총 2회 진입, 2회 청산, 1승 1패, 합계 `-3.0pt`
  - 실제 진입 전략은 모두 `zukkumi_original` / `쭈꾸미 원본`
  - `indicator_basic`, `orb_paper`는 실제 진입 0회
  - `score_watch`는 관찰용이라 실제 진입으로 보지 않는다.
- 거래 1:
  - 진입: 2026-06-08 20:37:35 KST
  - 방향: LONG
  - 전략/셋업: `zukkumi_original` / `P라인 반등 롱 확인`
  - 진입가: 29434.25
  - 손절 기준: 29406.48 아래 5분봉 마감
  - 목표가: 29484.25
  - 결과: LOSS
  - 청산: 2026-06-08 20:45:00 KST
  - 청산가: 29381.25
  - 손익: -53.0pt
  - 근거: 일봉 P라인 29409.92 근접 후 회복, P라인 아래 5분봉 확정 이탈 실패, 회복봉 직전봉보다 높게 마감, EMA20/50 상승 우위, 시장 보조지표 롱 우호.
- 거래 2:
  - 진입: 2026-06-08 21:22:39 KST
  - 방향: LONG
  - 전략/셋업: `zukkumi_original` / `P라인 반등 롱 확인`
  - 진입가: 29431.25
  - 손절 기준: 29406.73 아래 5분봉 마감
  - 목표가: 29481.25
  - 결과: WIN
  - 청산: 2026-06-08 21:30:00 KST
  - 청산가: 29481.25
  - 손익: +50.0pt
  - 근거: 일봉 P라인 29409.92 근접 후 회복, P라인 아래 5분봉 확정 이탈 실패, 회복봉 직전봉보다 높게 마감, EMA20/50 상승 우위, 시장 보조지표 롱 우호.
- 후보/미진입:
  - 23시 중간 보고 기준 `zukkumi_original`: 후보 열림 5, 놓친 진입 74, 안 들어간 게 맞았던 후보 57.
  - 최종 보고 기준 `zukkumi_original`: 놓친 진입 64, 안 들어간 게 맞았던 후보 49.
  - 최종 보고 기준 `orb_paper`: 실제 진입 0, 놓친 진입 4, 안 들어간 게 맞았던 후보 1.
  - 최종 보고 기준 `score_watch`: 관찰 후보 74, 놓친 진입 44, 안 들어간 게 맞았던 후보 30.
- 보고/알림:
  - 2026-06-08 23:02:53 KST `DAILY_REPORT` / `23시 중간 보고` 생성됨.
  - 2026-06-09 06:13:52 KST `DAILY_REPORT` / `미국장 마감 최종 보고` 생성됨.
  - 그러나 텔레그램은 `telegram_skipped: not_configured_or_disabled`로 스킵됨.
- 원인:
  - 어제 리뷰/알림을 못 받은 핵심 원인은 매매 미발생이 아니라 Render 텔레그램 환경변수 미설정 또는 비활성 상태다.
- 다음 조치:
  - Render Environment에서 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`가 있는지 확인한다.
  - `TELEGRAM_PAPER_NOTIFY=false`가 있으면 제거하거나 `true`로 바꾼다.
