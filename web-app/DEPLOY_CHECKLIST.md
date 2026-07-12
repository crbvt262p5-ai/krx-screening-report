# Deploy Checklist

## 1. Supabase

1. Supabase 프로젝트 생성
2. SQL Editor에서 [schema.sql](/Users/taeheehong/Documents/Playground/web-app/supabase/schema.sql) 실행
3. 테스트용 데이터가 필요하면 [seed.sql](/Users/taeheehong/Documents/Playground/web-app/supabase/seed.sql) 실행
4. `dogs`, `products`, `feeding_logs`, `portfolio_positions` 테이블 생성 확인

## 2. Vercel

1. 저장소를 Vercel에 연결
2. Root Directory를 `web-app`으로 설정
3. Environment Variables 추가

```bash
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_APP_URL=
```

4. 첫 배포 실행
5. 배포 후 `/api/health` 응답 확인
6. `/portfolio`에서 수정 후 새로고침해도 값이 유지되는지 확인

## 3. iPhone Safari

1. 홈 화면 접속
2. 강아지 프로필 생성
3. 제품 검색
4. 수동 제품 등록
5. 급여 계산
6. 기록 저장
7. 홈 복귀 후 최근 기록 표시 확인
8. 필요하면 홈 화면에 추가

## 4. 확인 URL

- 홈: `/`
- 포트: `/portfolio`
- 검색: `/search`
- 제품 등록: `/products/new`
- 급여 계산: `/feeding`
- 헬스체크: `/api/health`

## 5. 출시 전 주의

- 현재 Supabase RLS 정책은 프로토타입용 공개 정책입니다.
- 정식 서비스 전에는 사용자 인증과 사용자별 데이터 분리가 필요합니다.
