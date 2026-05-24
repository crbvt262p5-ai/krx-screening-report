# 멍칼로리 계산기 Phase 1 구현 계획

## 1. 이번 단계에서 고정하는 결정

### 기술 스택

- 프론트엔드: `Next.js`
- 배포: `Vercel`
- DB: `Supabase Postgres`
- 외부 검색 소스: `Open Pet Food Facts + Open Food Facts`
- 자체 데이터 저장: `Supabase`의 `products`, `product_aliases`, `feeding_logs`, `dogs`

### 왜 이 조합으로 가는가

- `Vercel`은 HTTPS와 상시 접근 가능한 웹 배포에 적합하다.
- `Supabase`는 모바일 웹앱에서 필요한 Postgres + 간단한 관리에 유리하다.
- `Next.js`는 iPhone Safari 대응, 서버 액션/라우트 핸들러, PWA 대응 확장에 유리하다.
- 현재 로컬 Python 서버 + 임시 터널 방식은 더 이상 서비스 방식으로 사용하지 않는다.

## 2. Phase 1 목표

이번 단계의 완료 기준은 아래다.

- 아이폰 Safari에서 첫 진입이 정상 동작한다.
- 강아지 프로필 생성/수정이 된다.
- 사료/간식 검색이 된다.
- 검색 실패 시 수동 등록이 된다.
- 하루 급여 계산이 된다.
- 기록 저장/조회가 된다.
- Vercel 배포 주소로 항상 접속 가능하다.

## 3. 범위

### 포함

- 1마리 이상 강아지 프로필 관리
- 제품 검색
- 수동 제품 추가
- 오늘 급여 입력
- 칼로리 계산
- 기록 저장 및 최근 기록 조회
- 모바일 대응 UI

### 제외

- 로그인/회원가입
- 바코드 스캔
- 관리자 페이지
- 자동 추천 알고리즘 고도화
- 앱스토어 네이티브 앱

## 4. 데이터 구조

### dogs

- id
- name
- weight_kg
- age_group
- activity_factor
- is_neutered
- created_at
- updated_at

### products

- id
- source_type
- external_id
- kind
- name
- brand
- total_weight_g
- kcal_per_100g
- total_kcal
- pieces_per_pack
- kcal_per_piece
- image_url
- verified
- created_at
- updated_at

### product_aliases

- id
- product_id
- alias
- locale

### feeding_logs

- id
- dog_id
- log_date
- food_product_id
- treat_product_id
- food_grams
- treat_pieces
- food_kcal
- treat_kcal
- total_kcal
- recommended_kcal
- note
- created_at

## 5. 검색 로직

### 우선순위

1. `products` + `product_aliases`에서 검색
2. 외부 API 조회
3. 검색 실패 시 수동 등록 유도

### 외부 API 사용 방식

- 사용자 검색어 원문 조회
- 강아지 관련 보조 키워드로 보정 조회
- 결과를 정규화해서 `products` 후보 포맷으로 매핑
- 사용자가 선택한 외부 제품은 로컬 DB에 캐싱

### 랭킹 규칙

- verified 제품 우선
- alias 정확 일치 우선
- kind 일치 우선
- kcal 존재 제품 우선
- 한국어/브랜드 매칭 우선

## 6. 화면 구성

### 화면 1: 강아지 선택

- 등록된 강아지 카드 목록
- 새 강아지 추가 버튼
- 최근 기록 바로가기

### 화면 2: 강아지 프로필 생성/수정

- 이름
- 체중
- 연령군
- 활동량

### 화면 3: 오늘 급여 입력

- 사료 섹션
- 간식 섹션
- 각각 제품 검색 버튼
- 각각 수동 입력 버튼
- 오늘 급여량만 기본 노출

### 화면 4: 제품 검색

- 사료/간식 탭
- 검색 입력
- 추천 결과
- 외부 결과
- 결과 없음 시 수동 추가 CTA

### 화면 5: 계산 결과

- 사료 kcal
- 간식 kcal
- 총 kcal
- 권장 kcal 비교
- 오늘 기록 저장

### 화면 6: 최근 기록

- 날짜별 카드
- 총칼로리
- 사료/간식 분리 수치

## 7. 모바일 UI 원칙

- 아이폰 세로 화면 기준 우선 설계
- 모든 CTA 버튼은 하단 thumb zone에 가깝게 배치
- 입력 단계는 한 화면에 1개 목적만 담기
- 결과 카드는 2열보다 1열 우선
- 고급 입력은 기본 숨김
- 인앱브라우저에서도 텍스트가 깨지지 않도록 단순 구조 유지

## 8. 구현 순서

### Step 1. 새 앱 베이스 생성

- Next.js 앱 생성
- 기본 라우팅 구성
- 모바일 레이아웃 시스템 구축

### Step 2. DB 연결

- Supabase 프로젝트 생성
- 테이블/인덱스 설계
- 초기 마이그레이션 작성

### Step 3. 프로필 기능

- 강아지 목록
- 강아지 생성/수정
- 기본 권장 칼로리 계산

### Step 4. 제품 검색 기능

- 로컬 DB 검색
- 외부 API 조회
- 결과 정규화
- 선택 제품 캐싱

### Step 5. 계산 기능

- 사료 kcal 계산
- 간식 kcal 계산
- 총합 및 권장량 비교

### Step 6. 기록 기능

- feeding_logs 저장
- 최근 기록 리스트

### Step 7. 배포

- Vercel 배포
- 환경변수 연결
- Supabase 연결 검증

### Step 8. 아이폰 테스트

- iPhone Safari
- iPhone Chrome
- 새로고침/뒤로가기/저장 흐름 검증

## 9. 테스트 체크리스트

### 기능

- 강아지 생성 가능
- 강아지 수정 가능
- 제품 검색 가능
- 외부 결과 선택 가능
- 수동 제품 등록 가능
- 계산 가능
- 저장 가능
- 기록 재조회 가능

### 모바일

- iPhone Safari 첫 진입
- 폼 입력
- 키보드 오픈 시 레이아웃 유지
- 버튼 탭 영역 정상
- 페이지 전환 정상

### 검색

- 한국어 브랜드 검색
- 영문 브랜드 검색
- 결과 없음 처리
- kcal 누락 제품 처리

## 10. 바로 다음 작업

다음 구현 세션에서는 아래부터 시작한다.

1. 현재 Python 프로토타입은 참고용으로만 두고 정식 `web-app` 구조를 새로 만든다.
2. Next.js 앱 스캐폴딩
3. Supabase용 SQL 스키마 초안 작성
4. 첫 화면을 `강아지 선택` 화면으로 구현
