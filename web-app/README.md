# Dog Food Tracker Web App

강아지 프로필을 기준으로 사료/간식 칼로리를 계산하고, 하루 급여 기록까지 남기는 모바일 우선 웹앱입니다.

## 현재 구현 범위

- 강아지 프로필 추가/수정
- 사료/간식 검색
- 외부 검색: Open Food Facts 계열
- 수동 제품 등록
- 급여 계산 및 기록 저장
- 포트폴리오 대시보드 `/portfolio`
- `localStorage fallback` + `Supabase 연결 준비`

## 로컬 실행

```bash
npm install
npm run dev
```

브라우저에서 [http://localhost:3000](http://localhost:3000) 로 확인합니다.

## 환경변수

`.env.local` 파일에 아래 값을 넣습니다.

```bash
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

Supabase 값이 없으면 목데이터와 브라우저 저장소로 동작합니다.

## Supabase 세팅

1. Supabase 프로젝트 생성
2. SQL Editor에서 [schema.sql](/Users/taeheehong/Documents/Playground/web-app/supabase/schema.sql) 실행
3. 원하면 [seed.sql](/Users/taeheehong/Documents/Playground/web-app/supabase/seed.sql)도 이어서 실행
4. Project Settings -> API 에서 `URL`, `anon key` 복사
5. `.env.local`에 환경변수 입력

현재 스키마는 프로토타입 속도를 위해 public read/write 정책으로 열려 있습니다. 정식 서비스 전에는 사용자 인증과 사용자별 정책으로 바꾸는 게 맞습니다.

## 포트 대시보드 저장

- Supabase 환경변수가 있으면 `/portfolio` 저장은 `portfolio_positions` 테이블에 기록됩니다.
- Supabase가 없으면 로컬에서는 `../data/portfolio_positions.csv`로 fallback 됩니다.
- 배포 환경에서는 앱 내부 시드 데이터를 먼저 보여주고, 첫 저장부터 Supabase에 영구 반영됩니다.

## Vercel 배포

1. Git 저장소를 Vercel에 연결
2. Framework Preset은 `Next.js`
3. Environment Variables에 Supabase 값 입력
4. 첫 배포 후 도메인 확인
5. iPhone Safari에서 프로필 생성 -> 검색 -> 계산 -> 저장 흐름 확인
6. `/portfolio` 접속 후 편집 저장이 유지되는지 확인

프로덕션에서는 `NEXT_PUBLIC_APP_URL`을 실제 배포 주소로 바꿔두는 편이 좋습니다.

## 확인한 명령

```bash
npm run lint
npm run build -- --webpack
```

이 저장소에서는 위 두 명령 기준으로 검증하고 있습니다.
