# KRX Automated Screening

KOSPI/KOSDAQ 전체 종목을 매일 자동으로 수집하고, 장 마감 후 Value bucket / Growth early bucket 리포트를 만드는 파이프라인입니다.

## Features

- 수동 종목코드 입력 없이 KRX 전체 종목코드 자동 갱신
- 전일 종가, 시가총액, PER, PBR, 최근배당수익률(Trailing), 평년화 배당수익률(Normalized) 자동 수집
- 최근 1/3/6/12개월 수익률과 52주 고점 대비 위치 자동 계산
- 최근 3년 매출/영업이익/순이익/배당 기록과 부채비율, FCF 가능한 범위 계산
- 최근 급등 종목 자동 제외 또는 경고 태그 부여
- 데이터 소스 실패 시 fallback 시도, 없으면 `missing_data` 플래그만 남기고 계속 진행
- `reports/daily_YYYY-MM-DD.md`, `data/screened_YYYY-MM-DD.csv`, `logs/*.log` 생성

## Data Sources

- `pykrx`: KRX 전체 종목리스트, 전일 종가, 시총, PER/PBR/DIV, 가격 이력
- `FinanceDataReader`: 가격 이력 및 종목리스트 fallback
- `DART Open API`: 선택적 재무 보강 소스
- `FnGuide` 공개 페이지: 기본 재무/배당/컨센서스 보강 소스
- Google News RSS: Growth early 후보군 뉴스 키워드 점검

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`python3 -m krx_screening.main` 실행 시 프로젝트 루트의 `.env`를 자동으로 읽습니다.

`.env`에 기본적으로 아래 값을 넣으면 됩니다.

```env
KRX_TIMEZONE=Asia/Seoul
KRX_MAX_WORKERS=8
KRX_NEWS_CANDIDATE_LIMIT=80
KRX_USE_DART=0
```

기본값은 안정 운용 모드이며 `FnGuide`/`FinanceDataReader` 중심으로 동작합니다.

DART를 실험적으로 켜고 싶을 때만 아래를 추가하세요.

```env
KRX_USE_DART=1
DART_API_KEY=your_dart_key
KRX_DART_MAX_CONCURRENT=2
```

현재 권장 운영 방식은 `KRX_USE_DART=0` 입니다. DART는 환경에 따라 연결 리셋이 발생할 수 있어, 비교 실험이나 추가 보강이 필요할 때만 켜는 편이 안정적입니다.

## Run

```bash
python3 -m krx_screening.main
```

또는 cron/launchd용 실행 스크립트:

```bash
/Users/taeheehong/Documents/Playground/run_krx_screening.sh
```

launchd 설치를 한 번에 끝내려면:

```bash
/Users/taeheehong/Documents/Playground/install_krx_launchd.sh
```

## Outputs

- Markdown: `/Users/taeheehong/Documents/Playground/reports/daily_YYYY-MM-DD.md`
- HTML Dashboard: `/Users/taeheehong/Documents/Playground/reports/daily_YYYY-MM-DD.html`
- CSV: `/Users/taeheehong/Documents/Playground/data/screened_YYYY-MM-DD.csv`
- Logs: `/Users/taeheehong/Documents/Playground/logs/krx_screening_YYYY-MM-DD.log`

최신 결과는 고정 경로로도 같이 저장됩니다.

- HTML Dashboard: `/Users/taeheehong/Documents/Playground/reports/latest.html`
- Markdown: `/Users/taeheehong/Documents/Playground/reports/latest.md`
- CSV: `/Users/taeheehong/Documents/Playground/data/latest.csv`

Markdown 리포트에는 아래가 포함됩니다.

- 요약 통계
- `Quick Picks` 형태의 Value/Growth 상위 10개 한줄 요약
- Value Top 20 표
- Growth Early Top 20 표

CSV에는 아래 값이 포함됩니다.

- 티커, 종목명, 시장
- 전일 종가, 시가총액
- PER, PBR, 배당수익률
- 최근배당수익률(`dividend_yield_trailing`)
- 평년화 배당수익률(`dividend_yield_normalized`)
- 최근 1/3/6/12개월 상승률
- 52주 고점 대비 위치
- 최근 3년 매출/영업이익/순이익/배당
- 영업이익 변동성, 부채비율, FCF, 순현금
- Value Score, Growth Early Score, Dividend Potential Score
- 제외/통과 사유, 단계 판정, 태그, `missing_data`

## Portfolio Overlay

스크리닝 리포트 위에 내 보유 종목 운영판을 덧씌우려면 아래 파일을 추가하면 됩니다.

- 템플릿: `/Users/taeheehong/Documents/Playground/krx_screening/portfolio_positions.template.csv`
- 실제 입력 파일: `/Users/taeheehong/Documents/Playground/data/portfolio_positions.csv`

예시 절차:

```bash
cp /Users/taeheehong/Documents/Playground/krx_screening/portfolio_positions.template.csv \
  /Users/taeheehong/Documents/Playground/data/portfolio_positions.csv
```

주요 컬럼:

- `ticker`: 6자리 종목코드
- `name`: 선택 입력, 비워두면 스크리닝 데이터의 종목명을 사용
- `market_scope`: `국내` / `해외`
- `asset_class`: `주식` / `ETF` / `리츠` 등
- `country`: 한국, 미국, 일본처럼 국가 구분
- `theme`: 반도체, 금융, 방산처럼 내가 보는 테마
- `sub_theme`: HBM, 은행, 지주사, 배당 ETF처럼 한 단계 더 세부 분류
- `strategy`: 배당, 턴어라운드, 성장, 트레이딩 등 운영 전략
- `style_bucket`: `성장`, `인컴`, `패시브`, `혼합` 같은 스타일 분류
- `trend_view`: `추세 초기`, `추세 진행`, `과열 경계`, `추세 확인 필요`
- `cycle_view`: `주도`, `리더 후보`, `상승 사이클`, `과열 구간`, `중립`
- `conviction`: `핵심`, `중간`, `위성`
- `fx_exposure`: `높음`, `낮음`
- `timing_view`: 초입 분할, 눌림 대기, 실적 확인 후 등 매수 타이밍 메모
- `actual_weight_pct`: 현재 실제 비중
- `target_weight_pct`: 목표 비중
- `planned_action`: 직접 `추가매수 검토`, `비중축소 검토`, `정리 검토`, `보유 유지` 등을 넣을 수 있음
- `notes`: 전략 수정 이유나 체크포인트 메모

비워 둬도 되는 컬럼:

- `market_scope`, `asset_class`, `country`, `style_bucket`, `trend_view`, `cycle_view`, `conviction`, `fx_exposure`

이 값들은 비어 있으면 리포트가 티커/시장/ETF 이름 패턴/스크리닝 stage를 보고 자동으로 임시 분류합니다.

이 파일이 있으면 HTML/Markdown 리포트 상단에 아래가 자동으로 추가됩니다.

- 테마별 실제 비중 vs 목표 비중
- 국내/해외 비중, 주식/ETF 비중
- 추세 분류별 비중
- 추가매수/축소/정리 액션 버킷
- 스크리닝 결과를 덮어쓴 리뷰 우선순위 큐

## Scoring Rules

### Value bucket

- `PER <= 10`, `PBR <= 1` 우선 가점
- `배당수익률 >= 2%` 가점
- 최근 6개월 `100%+` 상승 종목 제외
- 최근 12개월 `200%+` 상승 종목 제외
- 최근 3년 영업이익 연속 흑자 가점
- 현금성 자산/순현금 비중이 높으면 가점
- `FCF > 0` 이고 배당성향이 낮으면 `배당상향 잠재` 태그

### Growth early bucket

- 높은 현재 PER 허용
- 내년 예상 이익 성장률 `40%+` 우선
- 공급부족, ASP 상승, 가동률 상승, 고부가 믹스 전환 키워드 가점
- 최근 6개월 급등 시 `이미 반영`
- 52주 신고가 근처이거나 12개월 급등 시 `추격주의`

## Automation

### Cron

한국 장 마감 후 16:10 KST 실행 예시:

```cron
10 16 * * 1-5 /Users/taeheehong/Documents/Playground/run_krx_screening.sh
```

### launchd (macOS)

템플릿 파일:

`/Users/taeheehong/Documents/Playground/automation/com.playground.krx-screening.plist`

등록 예시:

```bash
mkdir -p ~/Library/LaunchAgents
cp /Users/taeheehong/Documents/Playground/automation/com.playground.krx-screening.plist ~/Library/LaunchAgents/
launchctl unload ~/Library/LaunchAgents/com.playground.krx-screening.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.playground.krx-screening.plist
```

또는 아래 설치 스크립트를 써도 됩니다.

```bash
/Users/taeheehong/Documents/Playground/install_krx_launchd.sh
```

## Mobile And Cloud Delivery

맥북이 꺼져 있어도 휴대폰에서 보려면, 실행과 배포를 GitHub Actions로 옮기는 편이 가장 간단합니다.

이 저장소에는 아래 파일이 이미 준비돼 있습니다.

- GitHub Actions: `/Users/taeheehong/Documents/Playground/.github/workflows/krx-pages.yml`
- Pages site builder: `/Users/taeheehong/Documents/Playground/scripts/build_pages_site.py`
- Telegram notifier: `/Users/taeheehong/Documents/Playground/scripts/send_krx_telegram.py`

동작 방식은 아래와 같습니다.

1. GitHub Actions가 평일 한국 시간 16:25에 스크리닝을 실행합니다.
2. 최신 HTML 리포트를 정적 사이트로 묶어서 GitHub Pages에 배포합니다.
3. 선택적으로 Telegram 봇으로 휴대폰에 링크와 요약을 보냅니다.

### GitHub Setup

1. 이 프로젝트를 GitHub 저장소로 올립니다.
2. GitHub 저장소 `Settings > Pages` 에서 배포 소스를 `GitHub Actions` 로 선택합니다.
3. `Settings > Secrets and variables > Actions` 에 아래 시크릿을 추가합니다.

필수 시크릿:

- `KRX_USE_DART`
- `DART_API_KEY` 선택

Telegram 알림까지 쓸 때:

- `KRX_TELEGRAM_BOT_TOKEN`
- `KRX_TELEGRAM_CHAT_ID`

### Telegram Bot Setup

1. Telegram에서 `@BotFather` 로 새 봇을 만듭니다.
2. 발급된 토큰을 `KRX_TELEGRAM_BOT_TOKEN` 으로 저장합니다.
3. 메시지를 받을 본인 채팅 또는 그룹의 chat id를 `KRX_TELEGRAM_CHAT_ID` 로 저장합니다.
4. Actions 실행이 끝나면 GitHub Pages URL이 포함된 요약 메시지를 받습니다.

### Local Site Build Test

로컬에서도 Pages 산출물을 미리 확인할 수 있습니다.

```bash
python3 scripts/build_pages_site.py
open /Users/taeheehong/Documents/Playground/site/index.html
```

## Failure Handling

- 개별 종목 재무 데이터가 비면 전체 실행을 멈추지 않습니다.
- DART를 켠 경우 실패 시 FnGuide fallback을 시도합니다.
- `pykrx` 가격 이력 실패 시 FinanceDataReader fallback을 시도합니다.
- 상세 실패 내용은 `logs/`에 남깁니다.
