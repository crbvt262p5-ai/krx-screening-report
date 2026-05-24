# 멍칼로리 계산기 제품 사양서

## 1. 목표

강아지 보호자가 사료와 간식의 칼로리를 빠르게 계산하고, 강아지별 하루 급여량을 관리할 수 있는 모바일 우선 앱을 만든다.

핵심 목표는 아래 4가지다.

- 항상 접속 가능해야 한다.
- 아이폰 Safari 환경에서 정상 동작해야 한다.
- 제품 검색이 실제 사용에 버틸 정도로 충분히 강해야 한다.
- 입력은 최소화하고 계산은 자동화해야 한다.

## 2. 배포 원칙

이 앱은 더 이상 로컬 맥북 서버에 의존하지 않는다.

- 개발 중 임시 확인: 로컬 서버 사용 가능
- 실제 사용/테스트: 항상 켜져 있는 정식 호스팅 사용
- 1차 권장 배포: Render 또는 Railway
- 2차 확장 배포: Vercel(프론트) + 별도 API/DB

배포 요구사항:

- HTTPS 필수
- 모바일 Safari에서 첫 진입, 저장, 검색, 새로고침이 모두 동작해야 함
- 서버 슬립 없이 상시 접근 가능해야 함
- 도메인은 나중에 커스텀 가능하도록 구조 분리

## 3. 아이폰 지원 기준

출시 기준 브라우저는 아래로 잡는다.

- iPhone Safari
- iPhone Chrome
- 카카오/인앱브라우저는 보조 대응 대상

우선순위:

1. Safari에서 완전 정상 동작
2. iOS Chrome에서도 동일 동작
3. 인앱브라우저는 깨질 경우 Safari로 열기 유도

기술 기준:

- HTML form 제출과 표준 fetch/XHR 모두 Safari 호환 방식으로 작성
- 반응형 레이아웃 필수
- 터치 타겟 44px 이상
- 고정 헤더/하단 버튼이 키보드와 충돌하지 않도록 구성
- PWA 대응 가능 구조로 설계

참고:

- Apple은 Safari에서 웹사이트/웹앱 경험과 디버깅 기능을 공식 제공한다.
- iPhone용 웹 콘텐츠는 표준 HTML/CSS/JS와 반응형 설계를 기준으로 만드는 것이 권장된다.

공식 참고:

- https://developer.apple.com/safari/
- https://developer.apple.com/documentation/safari-developer-tools
- https://developer.apple.com/library/archive/documentation/AppleApplications/Reference/SafariWebContent/Introduction/Introduction.html

## 4. 외부 데이터 소스 전략

### 최종 방침

단일 외부 DB 하나에 전적으로 의존하지 않는다.

검색/제품 데이터 구조는 아래 3단으로 간다.

1. 외부 기본 DB
2. 자체 보정 DB
3. 사용자 수동 등록 DB

### 4-1. 외부 기본 DB

기본 외부 DB는 아래로 고정한다.

- Open Pet Food Facts
- Open Food Facts API v2 호환 문서/엔드포인트

선정 이유:

- 공개 접근 가능
- 제품명 검색과 바코드 기반 조회 가능
- 총중량, 영양정보, 브랜드, 이미지 필드 확보 가능
- pet food 생태계와 연동됨

주의:

- 한국 제품 커버리지가 불완전할 수 있음
- 사용자 기여형 데이터라 품질 편차가 있음
- 1알 기준 kcal 같은 앱 전용 필드는 대부분 없음

공식 참고:

- https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/
- https://support.openfoodfacts.org/help/en-gb/10-open-pet-food-facts/102-where-can-i-find-the-open-pet-food-facts-api
- https://www.data.gouv.fr/datasets/open-pet-food-facts/

### 4-2. 자체 보정 DB

앱 품질을 책임지는 핵심 DB다.

저장 대상:

- 한국에서 많이 쓰는 사료/간식 제품
- 검색 별칭
- 브랜드 정규화
- kcal 보정값
- 1알당 kcal
- 포장당 개수
- 수동 검수 여부

역할:

- 외부 검색 실패 시 우선 노출
- 외부 데이터 오류 수정
- 한국어 검색 품질 향상
- 앱 계산에 필요한 추가 필드 보강

### 4-3. 사용자 수동 등록 DB

검색 실패 제품을 사용자가 직접 등록할 수 있게 한다.

저장 대상:

- 제품명
- 브랜드
- 제품 종류(사료/간식)
- 총중량
- 총칼로리 또는 100g당 kcal
- 전체 개수(간식일 때)
- 메모

역할:

- 즉시 계산 가능하게 함
- 나중에 자체 보정 DB 후보로 승격

## 5. 검색 전략

검색 우선순위는 아래로 고정한다.

1. 자체 보정 DB
2. 외부 DB(Open Pet Food Facts / Open Food Facts)
3. 수동 등록 유도

검색 방식:

- 정확 일치
- 별칭 일치
- 브랜드 + 제품명 조합
- 품목 키워드 보정
- 한글/영문 혼합 검색

검색 결과 랭킹 기준:

- 자체 보정 DB 여부
- 정확 일치 여부
- 브랜드 일치
- 제품 종류 일치(사료/간식)
- kcal 데이터 존재 여부
- 총중량 데이터 존재 여부
- 최근 사용 빈도

## 6. 사용자 플로우

### 1단계: 강아지 선택

- 기존 프로필 목록 노출
- 없으면 신규 프로필 생성

### 2단계: 오늘 급여 입력

- 사료 추가
- 간식 추가
- 제품 검색 후 선택
- 검색 실패 시 직접 입력

### 3단계: 자동 계산

- 사료 kcal 자동 계산
- 간식 kcal 자동 계산
- 하루 총칼로리 계산
- 권장 하루 칼로리 대비 비교

### 4단계: 저장

- 오늘 기록 저장
- 최근 기록 조회

## 7. 화면 구조

### 홈

- 강아지 프로필 카드
- 오늘 기록 시작 버튼
- 최근 기록 바로가기

### 프로필 생성/수정

- 이름
- 체중
- 연령군
- 활동량
- 중성화 여부(2차)
- 목표 체형(2차)

### 제품 검색 화면

- 사료/간식 탭
- 검색창
- 추천/최근 사용 제품
- 외부 검색 결과
- 수동 등록 버튼

### 계산 화면

- 선택된 사료
- 선택된 간식
- 급여량만 기본 입력
- 고급 보정은 접기
- 총칼로리, 권장량 비교, 저장 버튼

## 8. 입력 최소화 원칙

기본 입력은 아래만 남긴다.

- 사료: 오늘 먹인 g
- 간식: 오늘 먹인 개수

숨김 또는 고급 입력:

- 100g당 kcal
- 총칼로리
- 총 개수
- 총중량

원칙:

- 제품 선택만 제대로 되면 대부분 자동 계산
- 사용자는 “오늘 얼마나 먹였는지”만 넣으면 되게 함

## 9. 기술 구조

1차 구현 권장:

- 프론트: Next.js
- 백엔드: Next.js Route Handler 또는 FastAPI
- DB: Supabase Postgres
- 이미지/정적: Supabase Storage 또는 Vercel

현재 프로토타입에서 정식 전환 방향:

- Python 단일 파일 서버는 프로토타입까지만
- 정식 버전은 서버/DB 분리
- 데이터 모델과 검색 로직을 DB 중심으로 재작성

## 10. 데이터 모델 초안

### dogs

- id
- name
- weight_kg
- age_group
- activity_factor
- created_at
- updated_at

### products

- id
- source_type
- external_id
- kind
- name
- brand
- aliases
- total_weight_g
- kcal_per_100g
- total_kcal
- pieces_per_pack
- kcal_per_piece
- image_url
- verified
- created_at
- updated_at

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

## 11. 테스트 기준

반드시 아래를 통과해야 출시 가능으로 본다.

### 기능 테스트

- 프로필 생성
- 프로필 수정
- 사료 검색
- 간식 검색
- 수동 제품 등록
- 계산
- 기록 저장
- 기록 재조회

### 모바일 테스트

- iPhone Safari
- iPhone Chrome
- 세로 화면
- 작은 화면(미니급)
- 키보드 오픈 상태

### 데이터 테스트

- 외부 DB 결과 있음
- 외부 DB 결과 없음
- kcal 일부 누락
- 간식 개수만 있는 경우
- 사료 100g당 kcal만 있는 경우

## 12. 구현 우선순위

### Phase 1

- 정식 배포 환경 구성
- 강아지 프로필 관리
- 자체 DB 스키마
- 기본 검색/계산/기록
- iPhone Safari 검증

### Phase 2

- 외부 DB 연동 강화
- 수동 등록/보정 플로우
- 최근 사용/추천 검색
- PWA 아이콘/홈 화면 추가

### Phase 3

- 바코드 스캔
- 다견 프로필
- 급여 리포트
- 관리자 보정 도구

## 13. 이번 프로젝트의 확정 원칙

- “보여주기용 임시 터널”을 서비스 방식으로 쓰지 않는다.
- “외부 DB 하나면 되겠지”라는 가정으로 가지 않는다.
- “데이터 전략 + 배포 구조 + 모바일 기준”을 먼저 확정하고 구현한다.
- 아이폰 Safari에서 동작하지 않으면 완료로 보지 않는다.
