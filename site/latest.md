# KRX Daily Screening Report (2026-08-14)

## Summary
- Universe: 2763 종목
- Excluded by momentum rules: 192 종목
- Missing finance/data flags: 2763 종목
- Core missing fields: 1335 종목
- 실매수 검토: 19 종목
- Value Core: 16 종목
- Growth Core: 3 종목
- Cycle Leader: 2 종목
- Leader Candidate: 10 종목
- 소액 관찰: 69 종목
- 가치함정 경고: 103 종목
- Historical cache assists: 2639 종목

## Bucket Definitions
- `Value Core`: 거래대금 20D 100억 이상, `investability >= 3.0`, `business >= 5.0`, `cashflow >= 1.0`. 저평가 근거와 사업 지속성이 함께 보여야 합니다.
- `Growth Core`: 거래대금 20D 100억 이상, `investability >= 3.0`, `business >= 5.0`, `cashflow >= 1.0`. `Growth Proven`과 추정치/수급/TAM 중 최소 두 축이 확인돼야 합니다.
- `Cycle Leader`: 최근 3개월 시장 대비 초과수익, 업종 내 상위 상대강도, 정배열, 거래대금, 수급이 동시에 붙는 종목입니다.
- `Leader Candidate`: 업종은 강하고 정배열/추정치가 살아 있으나, 아직 완전한 리더 확신까지는 아닌 후보입니다.
- `Value Conviction`: `PER <= 20` 또는 `PBR <= 1.5` 또는 업종 할인 20% 이상, 사업체력/현금흐름 양호.
- `Growth Conviction`: `Growth Proven`, `estimate_revision >= 3.0`, `business >= 5.0`, `cashflow >= 1.0`, `stage != 과열`, 고PER면 정당화 태그 필요.
- `정배열 추세`: `종가 >= 20일선 >= 60일선 >= 120일선`이면 `조기매도 경계` 또는 `추세 유지` 태그를 붙여, 가치 해소 뒤에도 추세 지속 여부를 확인합니다.
- `테마 판정`: 업종명만으로 붙이지 않습니다. 업종/세부산업 + 뉴스/공시 + 체급/유동성 게이트를 통과해야 확정되고, 아니면 `미분류` 또는 `테마 보류`로 둡니다.
- `소액 관찰`: 논리는 유지되지만 유동성/체급/투자가능성 중 일부 부족. 보통 `최종점수 >= 22`, `business >= 3.8`, `cashflow >= 0`.
- `보류`: 재평가 신호는 있으나 핵심 게이트 일부 미달. 상단 추천보다는 추가 검증 대상입니다.
- `가치함정 경고`: `value_trap_risk` 높거나 거버넌스 할인 의심. 싸 보여도 할인 이유 먼저 확인.
- `제외`: 급등 제외, 최소 현실성 게이트 미통과, 현금흐름 심각 훼손 등.

## Quick Picks
### Value Core
- 현대위아 (011210) [KOSPI Mid] Value Core / score 40.0, 6M 21.1%, stage 중간 / 산업 대비 저평가|재평가 후보
- LG유플러스 (032640) [통신 Large] Value Core / score 38.1, 6M 4.7%, stage 후반 / 수급 개선|재평가 후보
- 삼성증권 (016360) [증권 Large] Value Core / score 37.8, 6M 45.4%, stage 중간 / 산업 대비 저평가|Leader Candidate|재평가 후보|배당 불안정
- 코오롱인더 (120110) [화학 Mid] Value Core / score 36.5, 6M 64.0%, stage 후반 / 산업 대비 저평가|주주환원 변화|지배구조 개편 가능성|상법 개정 수혜 가능성|재평가 후보 / 뉴스 코오롱인더, AI 소재·수출 호조에 1Q 실적 '서프라이즈’…목표가↑-IBK, 코오롱인더, 잠정실적 후 차익실현에 하락 마감 : 기업주식정보
- 한국금융지주 (071050) [금융 Mega] Value Core / score 35.9, 6M 46.2%, stage 중간 / 특별배당 가능성|재평가 후보|배당 불안정
- 에스엘 (005850) [KOSPI Large] Value Core / score 33.6, 6M 54.4%, stage 후반 / 특별배당 가능성|산업 대비 저평가|수급 개선|재평가 후보|배당 불안정
- KT (030200) [통신 Mega] Value Core / score 32.3, 6M 3.4%, stage 중간 / Follower|수급 개선|재평가 후보
- DN오토모티브 (007340) [KOSPI Large] Value Core / score 31.9, 6M 62.2%, stage 후반 / 산업 대비 저평가
- 세아베스틸지주 (001430) [금속 Mid] Value Core / score 30.1, 6M 69.2%, stage 후반 / 산업 대비 저평가
- 비에이치 (090460) [KOSPI Mid] Value Core / score 29.7, 6M 46.6%, stage 중간 / 산업 대비 저평가|수급 개선 / 뉴스 비에이치 주가 장중 7%대 상승, 증권가 2분기 실적 시장 기대치 상회 전망, 비에이치 주가 장중 8%대 상승, 애플 폴더블폰 수혜 기대에 목표주가 상향

### Growth Core
- HD현대 (267250) [금융 Mega] Growth Core / score 49.8, 6M 21.7%, stage 중간 / 산업 대비 저평가|TAM 확대|수급 개선|재평가 후보|배당 감액 이력
- HD현대마린솔루션 (443060) [일반서비스 Large] Growth Core / score 44.6, 6M 31.8%, stage 후반 / 산업 대비 저평가|Leader Candidate|TAM 확대|수급 개선|재평가 후보
- 고려아연 (010130) [금속 Mega] Growth Core / score 40.7, 6M -8.4%, stage 초입 / 산업 대비 저평가|재평가 후보

### Cycle Leader
- SK스퀘어 (402340) [금융 Mega] Leader / score 9.0, 6M 337.4%, stage 과열 / 이미 반영|추격주의|추격주의|산업 대비 저평가|Cycle Leader|수급 개선|주주환원 변화|상법 개정 수혜 가능성|최근 자사주 소각|재평가 후보 / 뉴스 SK스퀘어, 자사주 430억원 소각 결의…주주가치 제고, SK스퀘어, 자사주 3만4천388주 소각…약 431억원 규모
- 삼화콘덴서 (001820) [KOSPI Mid] Leader / score 8.2, 6M 296.9%, stage 과열 / 이미 반영|추격주의|산업 대비 저평가|Leader Candidate|수급 개선

### Leader Candidate
- 현대모비스 (012330) [KOSPI Mega] Leader Candidate / score 7.7, 6M 90.0%, stage 후반 / 산업 대비 저평가|Leader Candidate|수급 개선|재평가 후보
- HD현대마린솔루션 (443060) [일반서비스 Large] Growth Core / score 7.5, 6M 31.8%, stage 후반 / 산업 대비 저평가|Leader Candidate|TAM 확대|수급 개선|재평가 후보
- SK텔레콤 (017670) [통신 Mega] Leader Candidate / score 7.5, 6M 91.1%, stage 후반 / Leader Candidate|수급 개선|재평가 후보|감액배당 주의|배당 불안정|배당 감액 이력
- 삼성전기 (009150) [KOSPI Mega] Leader Candidate / score 7.4, 6M 556.7%, stage 과열 / 이미 반영|추격주의|산업 대비 저평가|Leader Candidate|수급 개선|재평가 후보|배당 불안정
- 한국타이어앤테크놀로지 (161390) [화학 Large] Leader Candidate / score 7.3, 6M 13.9%, stage 후반 / 산업 대비 저평가|Leader Candidate|수급 개선|재평가 후보
- 더블유게임즈 (192080) [IT 서비스 Mid] Leader Candidate / score 6.8, 6M 29.6%, stage 후반 / 추격주의|산업 대비 저평가|Leader Candidate|수급 개선|재평가 후보|이익생산 약한 섹터
- 삼성증권 (016360) [증권 Large] Value Core / score 6.7, 6M 45.4%, stage 중간 / 산업 대비 저평가|Leader Candidate|재평가 후보|배당 불안정
- NAVER (035420) [IT 서비스 Mega] Leader Candidate / score 6.7, 6M 0.2%, stage 중간 / 특별배당 가능성|산업 대비 저평가|Leader Candidate|수급 개선|재평가 후보|배당 불안정|이익생산 약한 섹터|배당 감액 이력
- 후성 (093370) [화학 Mid] Leader Candidate / score 6.6, 6M 130.4%, stage 과열 / 이미 반영|추격주의|추격주의|산업 대비 저평가|Leader Candidate|수급 개선|주주환원 변화|상법 개정 수혜 가능성|최근 자사주 소각|재평가 후보
- SK네트웍스 (001740) [유통 Mid] Leader Candidate / score 6.2, 6M 175.4%, stage 과열 / 이미 반영|추격주의|산업 대비 저평가|Leader Candidate|수급 개선|재평가 후보|배당 감액 이력

### 소액 관찰
- HD한국조선해양 (009540) [금융 Mega] 소액 관찰 / score 44.1, 6M -5.9%, stage 중간 / 산업 대비 저평가|Follower|TAM 확대|수급 개선|고PER 정당화 가능|재평가 후보|배당 불안정
- 대신증권 (003540) [증권 Mid] 소액 관찰 / score 38.7, 6M 5.0%, stage 초입 / 재평가 후보
- GS리테일 (007070) [유통 Large] Follower / score 38.1, 6M 7.4%, stage 중간 / 산업 대비 저평가|수급 개선|재평가 후보 / 뉴스 GS리테일·BGF리테일, 실적 좋은데 주가 힘 못쓰는 까닭
- 메디톡스 (086900) [제약 Mid] 소액 관찰 / score 37.1, 6M -33.0%, stage 초입 / 산업 대비 저평가|수급 개선|재평가 후보|이익생산 약한 섹터
- LX홀딩스 (383800) [금융 Mid] 소액 관찰 / score 36.5, 6M -1.2%, stage 중간 / 산업 대비 저평가|Follower|수급 개선|재평가 후보
- SNT에너지 (100840) [KOSPI Mid] 소액 관찰 / score 36.5, 6M -15.3%, stage 초입 / 특별배당 가능성|배당 불안정
- NHN (181710) [IT 서비스 Large] Follower / score 36.1, 6M 18.4%, stage 초입 / 산업 대비 저평가|수급 개선|주주환원 변화|상법 개정 수혜 가능성|최근 자사주 소각|재평가 후보 / 뉴스 메리츠증권 "NHN 주식 매수로 상향, 웹보드 규제완화에 실적 상승 전망, NHN, 167억 자사주 사서 전량 없앤다…3개년 주주환원 정책 본격 이행
- 한화 (000880) [화학 Large] 소액 관찰 / score 35.7, 6M 42.5%, stage 중간 / 산업 대비 저평가|수급 개선|재평가 후보
- HD현대중공업 (329180) [KOSPI Mega] Follower / score 34.6, 6M 21.7%, stage 중간 / TAM 확대|수급 개선|고PER 정당화 가능|재평가 후보|배당 불안정
- 한국앤컴퍼니 (000240) [금융 Large] Follower / score 34.6, 6M -4.7%, stage 중간 / 산업 대비 저평가|수급 개선|재평가 후보

### 가치함정 경고
- 모나용평 (070960) [일반서비스 Small] 가치함정 경고 / score 5.8, 6M -24.0%, stage 초입 / 유동성 주의|산업 대비 저평가|거버넌스 할인 의심|가치 함정 주의
- 아이에스동서 (010780) [비금속 Mid] 가치함정 경고 / score 5.6, 6M 42.3%, stage 중간 / 산업 대비 저평가|수급 개선|감액배당 주의|배당 불안정|배당 감액 이력|거버넌스 할인 의심|가치 함정 주의
- 한국철강 (104700) [금속 Mid] 가치함정 경고 / score 5.5, 6M -12.6%, stage 중간 / 산업 대비 저평가|Follower|배당 불안정|배당 감액 이력|거버넌스 할인 의심|가치 함정 주의
- 사조대림 (003960) [KOSPI Small] 가치함정 경고 / score 5.3, 6M -32.9%, stage 초입 / 유동성 주의|배당 감액 이력|거버넌스 할인 의심|가치 함정 주의
- SBS (034120) [KOSPI Small] 가치함정 경고 / score 5.2, 6M -35.9%, stage 초입 / 산업 대비 저평가|감액배당 주의|배당 감액 이력|거버넌스 할인 의심|가치 함정 주의
- 태영건설 (009410) [건설 Mid] 가치함정 경고 / score 5.0, 6M 3.3%, stage 초입 / 산업 대비 저평가|Follower|비경상 이익 의심|거버넌스 할인 의심|가치 함정 주의
- LX하우시스 (108670) [화학 Mid] 가치함정 경고 / score 4.6, 6M 9.9%, stage 중간 / 산업 대비 저평가|Follower|감액배당 주의|배당 감액 이력|거버넌스 할인 의심|가치 함정 주의
- 동국홀딩스 (001230) [금융 Mid] 가치함정 경고 / score 4.4, 6M 9.1%, stage 중간 / 산업 대비 저평가|감액배당 주의|배당 불안정|배당 감액 이력|거버넌스 할인 의심|가치 함정 주의
- 신원 (009270) [KOSPI Small] 가치함정 경고 / score 4.3, 6M -29.3%, stage 초입 / 배당 감액 이력|거버넌스 할인 의심|가치 함정 주의
- 한국제지 (027970) [KOSPI Small] 가치함정 경고 / score 4.2, 6M -16.3%, stage 중간 / 유동성 주의|가치 함정 주의

## Today's Important Issues
- 테크윙 (089030) [Follower] score 49.61: 뉴스 테크윙, 27억원 규모 자사주 소각 결정, [생생한 주식쇼 생쇼] 테크윙, HBM4 검사 장비 공급 확대로 중장기 성장 전망
- HD건설기계 (267270) [Follower] score 37.48: 뉴스 [잠정실적]HD건설기계, 올해 2Q 영업이익 급증 2489억원... 전년동기比 522%↑ (연결), HD건설기계, 자사주 5만2000주 소각
- 코오롱인더 (120110) [Value Core] score 36.55: 뉴스 코오롱인더, AI 소재·수출 호조에 1Q 실적 '서프라이즈’…목표가↑-IBK, 코오롱인더, 잠정실적 후 차익실현에 하락 마감 : 기업주식정보
- 한국가스공사 (036460) [Follower] score 31.59: 뉴스 [특징주] 한국가스공사, 잠정 실적·주총 기대감에 '들썩' : 기업주식정보, 한국가스공사, 잠정 실적 실망감에 2%대 하락 마감 : 기업주식정보
- 에스티아이 (039440) [소액 관찰] score 29.85: 뉴스 에스티아이 주가 장중 10%대 강세, 전력반도체 장비 수주에 52주 최고가, 에스티아이, 19억 규모 자사주 처분 결정
- 비에이치 (090460) [Value Core] score 29.73: 뉴스 비에이치 주가 장중 7%대 상승, 증권가 2분기 실적 시장 기대치 상회 전망, 비에이치 주가 장중 8%대 상승, 애플 폴더블폰 수혜 기대에 목표주가 상향
- 솔루엠 (248070) [보류] score 29.64: 뉴스 솔루엠, AI 데이터센터용 파워 사업 본격 확대…전성호 대표 “지속 성장에 대한 확신으로 자사 주식 매입, 솔루엠, AI 데이터센터용 800Vdc급 전력 솔루션 개발…포트폴리오 다각화
- SK스퀘어 (402340) [Leader] score 29.42: 뉴스 SK스퀘어, 자사주 430억원 소각 결의…주주가치 제고, SK스퀘어, 자사주 3만4천388주 소각…약 431억원 규모
- 삼미금속 (012210) [보류] score 29.21: 뉴스 삼미금속, 300억원 투자 유치 성공… 조선·방산·원전·AI 데이터센터 등 성장동력 강화, [모닝 리포트] "삼미금속, AI 데이터센터 전력 수요 수혜…선박 엔진·원전 성장
- 유니트론텍 (142210) [보류] score 28.89: 뉴스 유니트론텍, 전장 반도체 가격 상승에 분기 최대 실적…올해 PER 3.1배 초저평가-키움, 유니트론텍, 제30기 재무제표 승인·현금배당 주당 165원 확정
- 고영 (098460) [Follower] score 28.15: 뉴스 고영, 자기주식 450,542주 처분 및 소각...186억 원 규모, 고영, 주식소각 결정→주식수 감소
- 이지홀딩스 (035810) [소액 관찰] score 28.06: 뉴스 [특징주] 이지홀딩스, ‘폭탄 배당’ 소식에 29% 급등 - 조선비즈, [특징주]"돈도 잘벌고 배당도 잘 준다"…이지홀딩스, 29%↑

## Value Lenses
### Deep Value
- 풍산 (103140) [금속 Large] 보류 / score 37.5, 6M -26.5%, stage 초입 / 산업 대비 저평가|감액배당 주의|배당 불안정|배당 감액 이력
- 대신증권 (003540) [증권 Mid] 소액 관찰 / score 38.7, 6M 5.0%, stage 초입 / 재평가 후보
- 현대위아 (011210) [KOSPI Mid] Value Core / score 40.0, 6M 21.1%, stage 중간 / 산업 대비 저평가|재평가 후보
- 삼성증권 (016360) [증권 Large] Value Core / score 37.8, 6M 45.4%, stage 중간 / 산업 대비 저평가|Leader Candidate|재평가 후보|배당 불안정

### Dividend Compounder
_No rows_

### Turnaround Value
_No rows_

## Growth Lenses
### Growth Proven
- HD현대 (267250) [금융 Mega] Growth Core / score 20.6, 6M 21.7%, stage 중간 / 산업 대비 저평가|TAM 확대|수급 개선|재평가 후보|배당 감액 이력
- HD현대마린솔루션 (443060) [일반서비스 Large] Growth Core / score 16.6, 6M 31.8%, stage 후반 / 산업 대비 저평가|Leader Candidate|TAM 확대|수급 개선|재평가 후보
- 고려아연 (010130) [금속 Mega] Growth Core / score 15.7, 6M -8.4%, stage 초입 / 산업 대비 저평가|재평가 후보
- 한국콜마 (161890) [화학 Large] Follower / score 11.6, 6M 31.1%, stage 중간 / 산업 대비 저평가|재평가 후보
- 현대위아 (011210) [KOSPI Mid] Value Core / score 11.2, 6M 21.1%, stage 중간 / 산업 대비 저평가|재평가 후보

### Growth Speculative
- 디아이 (003160) [KOSPI Mid] 보류 / score 19.9, 6M 24.0%, stage 중간 / 특별배당 가능성|산업 대비 저평가|TAM 확대|고PER 정당화 가능|재평가 후보|배당 불안정|Core Watch / 뉴스 [뉴스락 주식네비 8월 19일] 디아이(003160), 완벽한 실적, 남은건 지속성, 디아이, HBM4 장비 납품 본격화에 2Q 영업익 192% 급증 전망-한국
- 테크윙 (089030) [KOSDAQ Mid] Follower / score 20.5, 6M 37.6%, stage 후반 / 산업 대비 저평가|TAM 확대|수급 개선|주주환원 변화|상법 개정 수혜 가능성|최근 자사주 소각|고PER 정당화 가능|재평가 후보 / 뉴스 테크윙, 27억원 규모 자사주 소각 결정, [생생한 주식쇼 생쇼] 테크윙, HBM4 검사 장비 공급 확대로 중장기 성장 전망
- 코나아이 (052400) [IT 서비스 Mid] 보류 / score 9.6, 6M 0.0%, stage 초입 / 산업 대비 저평가|수급 개선|재평가 후보|배당 불안정
- HD한국조선해양 (009540) [금융 Mega] 소액 관찰 / score 20.7, 6M -5.9%, stage 중간 / 산업 대비 저평가|Follower|TAM 확대|수급 개선|고PER 정당화 가능|재평가 후보|배당 불안정
- 키움증권 (039490) [증권 Large] 보류 / score 14.2, 6M 26.9%, stage 중간 / 산업 대비 저평가|재평가 후보|배당 불안정

## Missed Leader Detector
_No rows_

## Top Value Bucket
|   ticker | name      | core_bucket   | sector   | size_bucket   |     prev_close |    per |   peg |   roe_pct |   pbr |   dividend_yield_trailing |   dividend_yield_normalized |   returns_6m_pct |   final_score |   value_score |   estimate_revision_score |   tam_expansion_score |   ownership_flow_score |   policy_score |   dividend_potential_score |   business_quality_score |   liquidity_support_score | stage   | tags                                                                     | missing_data                                                                                        |
|---------:|:----------|:--------------|:---------|:--------------|---------------:|-------:|------:|----------:|------:|--------------------------:|----------------------------:|-----------------:|--------------:|--------------:|--------------------------:|----------------------:|-----------------------:|---------------:|---------------------------:|-------------------------:|--------------------------:|:--------|:-------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------|
|   003160 | 디아이       |               |          | Mid           |  25800         |  20.84 |  0.03 |       nan |  2.57 |                      0.97 |                        0.39 |            24.02 |         56.05 |         13.39 |                       6.2 |                  12   |                      0 |           0.8  |                       1.7  |                      5.6 |                       2.2 | 중간      | 특별배당 가능성|산업 대비 저평가|TAM 확대|고PER 정당화 가능|재평가 후보|배당 불안정|Core Watch           | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   089030 | 테크윙       |               |          | Mid           |  49250         |  22.97 |  0.03 |       nan |  5.96 |                      0.26 |                        0.26 |            37.62 |         49.61 |         10.22 |                       2.8 |                  11   |                      0 |           6.8  |                       0.13 |                      5.1 |                       3.6 | 후반      | 산업 대비 저평가|TAM 확대|수급 개선|주주환원 변화|상법 개정 수혜 가능성|최근 자사주 소각|고PER 정당화 가능|재평가 후보 | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   267250 | HD현대      | Growth Core   | 금융       | Mega          | 235500         |   8.45 |  0.06 |       nan |  0.87 |                      1.7  |                        1.57 |            21.7  |         49.79 |         18.37 |                       6.2 |                   5.8 |                      0 |           0    |                       0.79 |                      6.7 |                       3   | 중간      | 산업 대비 저평가|TAM 확대|수급 개선|재평가 후보|배당 감액 이력                                   | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   009540 | HD한국조선해양  |               | 금융       | Mega          | 386000         |  34.09 |  0.57 |       nan |  1.21 |                      3.19 |                        2.25 |            -5.91 |         44.09 |         14    |                       6.2 |                   6.8 |                      0 |           0    |                       1.12 |                      4.8 |                       3   | 중간      | 산업 대비 저평가|Follower|TAM 확대|수급 개선|고PER 정당화 가능|재평가 후보|배당 불안정                | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   443060 | HD현대마린솔루션 | Growth Core   | 일반서비스    | Large         | 196800         |  33.99 |  1.04 |       nan |  8.68 |                      2.01 |                        1.6  |            31.79 |         44.61 |         14.37 |                       5   |                   6.8 |                      0 |           0    |                       3.3  |                      9.5 |                       3   | 후반      | 산업 대비 저평가|Leader Candidate|TAM 확대|수급 개선|재평가 후보                           | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   003230 | 삼양식품      |               |          | Large         |      1.27e+06  |  14.56 |  0.34 |       nan |  7.72 |                      0.38 |                        0.26 |           -14.17 |         41.18 |          9.16 |                       6.2 |                   1.8 |                      0 |           0.8  |                       1.63 |                      6.3 |                       3   | 중간      | 수급 개선|재평가 후보|배당 불안정                                                      | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   010130 | 고려아연      | Growth Core   | 금속       | Mega          |      1.196e+06 |  12.79 |  0.2  |       nan |  1.83 |                      1.67 |                        1.46 |            -8.39 |         40.72 |         11.86 |                       5.4 |                   2.8 |                      0 |           0.8  |                       2.23 |                      6.3 |                       1.7 | 초입      | 산업 대비 저평가|재평가 후보                                                         | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   086450 | 동국제약      |               | 제약       | Mid           |  19720         |  18.86 |  0.53 |       nan |  1.11 |                      1.01 |                        1.01 |             0.1  |         38.1  |         12.39 |                       5   |                   0.8 |                      0 |           0    |                       0.39 |                      8.4 |                       1.7 | 초입      | 산업 대비 저평가|재평가 후보|이익생산 약한 섹터                                              | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   103140 | 풍산        |               | 금속       | Large         |  82000         |   3.59 |  0.05 |       nan |  0.79 |                      2.07 |                        2.07 |           -26.47 |         37.54 |         16.5  |                       3.2 |                   0.8 |                      0 |           0    |                       1.03 |                      7.5 |                       1.7 | 초입      | 산업 대비 저평가|감액배당 주의|배당 불안정|배당 감액 이력                                        | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   194700 | 노바렉스      |               |          | Small         |  14560         |  12.89 |  0.31 |       nan |  0.75 |                      2.75 |                        1.37 |             0.49 |         33.55 |         10.71 |                       6.2 |                   1   |                      0 |           0    |                       0.69 |                      7.5 |                       2   | 초입      | 특별배당 가능성|Follower|수급 개선|재평가 후보|배당 불안정                                    | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   053690 | 한미글로벌     |               | 일반서비스    | Small         |  18880         |  10.81 |  0.24 |       nan |  0.99 |                      2.12 |                        2.12 |             6.26 |         33.31 |         19.8  |                       4.2 |                   0.8 |                      0 |           0.8  |                       2.56 |                      8.4 |                       0.9 | 초입      | 산업 대비 저평가|Follower                                                       | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   061090 | 세나테크놀로지   |               |          | Small         |  45250         |  11.78 |  0.29 |       nan |  1.37 |                    nan    |                      nan    |            -7.75 |         31.33 |         10.87 |                       5   |                   0.8 |                      0 |           0    |                      -0.17 |                      7.5 |                       0.8 | 초입      | 산업 대비 저평가|Follower|재평가 후보|추세 유지                                          | dividend_yield|investor_flow_3m|etf_inclusion_change_3m|returns_12m|dividends_3y|eps_revision_score |
|   003540 | 대신증권      |               | 증권       | Mid           |  27200         |   9.06 |  0.12 |       nan |  0.43 |                      4.41 |                        4.41 |             4.96 |         38.72 |         14.3  |                       5.4 |                   1.8 |                      0 |           1.2  |                       2.21 |                      6.8 |                       1.4 | 초입      | 재평가 후보                                                                   | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   214450 | 파마리서치     |               | 제약       | Large         | 398000         |  16.74 |  0.55 |       nan |  6.81 |                      0.93 |                        0.28 |           -29.94 |         38.22 |         11.57 |                       5   |                   1.8 |                      0 |           0    |                      -0.14 |                      7.2 |                       2.2 | 초입      | 특별배당 가능성|산업 대비 저평가|Follower|재평가 후보|배당 불안정|이익생산 약한 섹터                     | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   012450 | 한화에어로스페이스 |               |          | Mega          |      1.16e+06  |  21.08 |  0.4  |       nan |  7.48 |                      0.6  |                        0.3  |            24.48 |         39.33 |         10.02 |                       6.2 |                   1.8 |                      0 |           0    |                       2.42 |                      5   |                       3   | 중간      | 특별배당 가능성|산업 대비 저평가|재평가 후보|배당 불안정                                         | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   054210 | 이랜텍       |               |          | Small         |   8090         |  26.66 |  0.43 |       nan |  0.72 |                      1.24 |                        0.99 |            -6.55 |         29.18 |          9.58 |                       6.2 |                   0   |                      0 |           0    |                       0.49 |                      6.8 |                       1.4 | 초입      | 재평가 후보                                                                   | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   011210 | 현대위아      | Value Core    |          | Mid           |  67800         |  19.94 |  0.33 |       nan |  0.35 |                      1.77 |                        1.62 |            21.1  |         40.05 |         19.24 |                       5   |                   0.8 |                      0 |           1.92 |                       2.31 |                      8.4 |                       2.2 | 중간      | 산업 대비 저평가|재평가 후보                                                         | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   052400 | 코나아이      |               | IT 서비스   | Mid           |  39950         |   9.77 |  0.24 |       nan |  1.78 |                      3    |                        1.7  |             0    |         40.98 |         14.08 |                       6.2 |                   0   |                      0 |           0    |                       0.85 |                      6.8 |                       2.8 | 초입      | 산업 대비 저평가|수급 개선|재평가 후보|배당 불안정                                            | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   112610 | 씨에스윈드     |               | 금속       | Mid           |  46850         | 116.31 |  0.28 |       nan |  1.42 |                      2.13 |                        2.13 |            -2.58 |         38.31 |         13.93 |                       6.2 |                   1   |                      0 |           0.8  |                       5.06 |                      5.9 |                       1.7 | 초입      | 산업 대비 저평가|재평가 후보|배당 불안정                                                  | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   016360 | 삼성증권      | Value Core    | 증권       | Large         |  93000         |   4.28 |  0.07 |       nan |  0.59 |                      4.3  |                        3.76 |            45.41 |         37.84 |         19.46 |                       4.4 |                   0   |                      0 |           1.2  |                       1.88 |                      5.4 |                       3   | 중간      | 산업 대비 저평가|Leader Candidate|재평가 후보|배당 불안정                                 | investor_flow_3m|etf_inclusion_change_3m|sales_3y|eps_revision_score                                |

## Top Growth Early Bucket
|   ticker | name      | sector   | size_bucket   |     prev_close |    per |   pbr |   returns_6m_pct |   high_52w_ratio_pct |   growth_early_score |   value_score | stage   | tags                                                                     | missing_data                                                                                        |
|---------:|:----------|:---------|:--------------|---------------:|-------:|------:|-----------------:|---------------------:|---------------------:|--------------:|:--------|:-------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------|
|   003160 | 디아이       |          | Mid           |  25800         |  20.84 |  2.57 |            24.02 |                73.29 |                19.92 |         13.39 | 중간      | 특별배당 가능성|산업 대비 저평가|TAM 확대|고PER 정당화 가능|재평가 후보|배당 불안정|Core Watch           | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   089030 | 테크윙       |          | Mid           |  49250         |  22.97 |  5.96 |            37.62 |                91.84 |                20.52 |         10.22 | 후반      | 산업 대비 저평가|TAM 확대|수급 개선|주주환원 변화|상법 개정 수혜 가능성|최근 자사주 소각|고PER 정당화 가능|재평가 후보 | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   267250 | HD현대      | 금융       | Mega          | 235500         |   8.45 |  0.87 |            21.7  |                78.58 |                20.65 |         18.37 | 중간      | 산업 대비 저평가|TAM 확대|수급 개선|재평가 후보|배당 감액 이력                                   | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   443060 | HD현대마린솔루션 | 일반서비스    | Large         | 196800         |  33.99 |  8.68 |            31.79 |                88.24 |                16.56 |         14.37 | 후반      | 산업 대비 저평가|Leader Candidate|TAM 확대|수급 개선|재평가 후보                           | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   052400 | 코나아이      | IT 서비스   | Mid           |  39950         |   9.77 |  1.78 |             0    |                61.67 |                 9.55 |         14.08 | 초입      | 산업 대비 저평가|수급 개선|재평가 후보|배당 불안정                                            | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   010130 | 고려아연      | 금속       | Mega          |      1.196e+06 |  12.79 |  1.83 |            -8.39 |                56.78 |                15.7  |         11.86 | 초입      | 산업 대비 저평가|재평가 후보                                                         | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   009540 | HD한국조선해양  | 금융       | Mega          | 386000         |  34.09 |  1.21 |            -5.91 |                83    |                20.71 |         14    | 중간      | 산업 대비 저평가|Follower|TAM 확대|수급 개선|고PER 정당화 가능|재평가 후보|배당 불안정                | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   161890 | 한국콜마      | 화학       | Large         | 136700         |  19.17 |  1.92 |            31.11 |                79.12 |                11.55 |         13.66 | 중간      | 산업 대비 저평가|재평가 후보                                                         | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   039490 | 키움증권      | 증권       | Large         | 300500         |   3.83 |  0.67 |            26.88 |                73.36 |                14.21 |         17.3  | 중간      | 산업 대비 저평가|재평가 후보|배당 불안정                                                  | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   194700 | 노바렉스      |          | Small         |  14560         |  12.89 |  0.75 |             0.49 |                65.82 |                10.89 |         10.71 | 초입      | 특별배당 가능성|Follower|수급 개선|재평가 후보|배당 불안정                                    | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   053690 | 한미글로벌     | 일반서비스    | Small         |  18880         |  10.81 |  0.99 |             6.26 |                58.25 |                 9.1  |         19.8  | 초입      | 산업 대비 저평가|Follower                                                       | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   061090 | 세나테크놀로지   |          | Small         |  45250         |  11.78 |  1.37 |            -7.75 |                56.42 |                 9.84 |         10.87 | 초입      | 산업 대비 저평가|Follower|재평가 후보|추세 유지                                          | dividend_yield|investor_flow_3m|etf_inclusion_change_3m|returns_12m|dividends_3y|eps_revision_score |
|   011210 | 현대위아      |          | Mid           |  67800         |  19.94 |  0.35 |            21.1  |                75.91 |                11.21 |         19.24 | 중간      | 산업 대비 저평가|재평가 후보                                                         | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   267260 | HD현대일렉트릭  |          | Mega          | 803000         |  11.51 |  7.45 |            37.8  |                79.58 |                12.82 |         11.96 | 중간      | 추격주의|산업 대비 저평가|수급 개선|재평가 후보|배당 불안정                                       | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   103590 | 일진전기      |          | Large         |  74300         |  13.46 |  2.33 |            50.92 |                56.77 |                14.43 |         12.26 | 후반      | 추격주의|산업 대비 저평가|Follower|재평가 후보|배당 불안정                                    | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   054210 | 이랜텍       |          | Small         |   8090         |  26.66 |  0.72 |            -6.55 |                65    |                 9.96 |          9.58 | 초입      | 재평가 후보                                                                   | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   003540 | 대신증권      | 증권       | Mid           |  27200         |   9.06 |  0.43 |             4.96 |                60.41 |                13.07 |         14.3  | 초입      | 재평가 후보                                                                   | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   003570 | SNT다이내믹스  |          | Mid           |  32600         |   4.82 |  1.18 |            -2.62 |                54.83 |                11.08 |         16.6  | 초입      | 산업 대비 저평가|재평가 후보|배당 불안정                                                  | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   112610 | 씨에스윈드     | 금속       | Mid           |  46850         | 116.31 |  1.42 |            -2.58 |                53.97 |                14.53 |         13.93 | 초입      | 산업 대비 저평가|재평가 후보|배당 불안정                                                  | investor_flow_3m|etf_inclusion_change_3m|eps_revision_score                                         |
|   232140 | 와이씨       |          | Mid           |  11100         |  13.46 |  3.26 |            10.97 |                67.43 |                13.51 |         12.63 | 초입      | 산업 대비 저평가|재평가 후보                                                         | dividend_yield|investor_flow_3m|etf_inclusion_change_3m|dividends_3y|eps_revision_score             |

## Special Dividend Watch
|   ticker | name      | sector   |   prev_close |   dividend_yield_trailing |   dividend_yield_normalized |   dividend_gap_pct | dividends_3y             | tags                                                |
|---------:|:----------|:---------|-------------:|--------------------------:|----------------------------:|-------------------:|:-------------------------|:----------------------------------------------------|
|   035810 | 이지홀딩스     |          |         4540 |                     29.98 |                        5.51 |              24.47 | 120.00|250.00|1361.00    | 특별배당 가능성|주주환원 변화|상법 개정 수혜 가능성|재평가 후보|배당 불안정         |
|   032960 | 동일기연      |          |         2240 |                     22.32 |                        1.88 |              20.44 | 32.00|42.00|500.00       | 특별배당 가능성|유동성 주의|산업 대비 저평가|배당 불안정|비경상 이익 의심|가치 함정 주의 |
|   285490 | 노바텍       |          |        12200 |                     23.53 |                       11.55 |              11.98 | 500.00|1409.00|2871.00   | 특별배당 가능성|배당 불안정|비경상 이익 의심|가치 함정 주의                  |
|   017800 | 현대엘리베이터   |          |        72500 |                     19.32 |                        7.59 |              11.73 | 4000.00|5500.00|14010.00 | 특별배당 가능성|산업 대비 저평가|배당 불안정                           |
|   339950 | 아이비김영     | 일반서비스    |         2875 |                     10.43 |                        1.04 |               9.39 | 20.00|30.00|300.00       | 특별배당 가능성|산업 대비 저평가|Follower|배당 불안정                  |
|   129890 | 앱코        |          |          970 |                     17.94 |                       10    |               7.94 | 20.00|174.00             | 유동성 주의|Follower|배당 불안정|비경상 이익 의심                    |
|   065710 | 서호전기      |          |        44500 |                     13.48 |                        5.62 |               7.86 | 1500.00|2500.00|6000.00  | 특별배당 가능성|수급 개선|재평가 후보|배당 불안정                        |
|   027710 | 팜스토리      |          |         1073 |                      9.32 |                        2.33 |               6.99 | 25.00|25.00|100.00       | 특별배당 가능성|배당 불안정                                     |
|   006980 | 우성        |          |        16310 |                      7.97 |                        1.84 |               6.13 | 300.00|300.00|1300.00    | 특별배당 가능성|유동성 주의|배당 불안정|거버넌스 할인 의심|가치 함정 주의          |
|   020710 | 시공테크      | 일반서비스    |         3660 |                      9.26 |                        3.28 |               5.98 | 80.00|120.00|339.00      | 특별배당 가능성|산업 대비 저평가|Follower|배당 불안정|비경상 이익 의심        |
|   277070 | 린드먼아시아    | 기타금융     |         2990 |                      8.36 |                        2.64 |               5.72 | 43.00|79.00|250.00       | 특별배당 가능성|유동성 주의|산업 대비 저평가|Follower|배당 불안정|가치 함정 주의  |
|   016450 | 한세예스24홀딩스 |          |         4400 |                     11.36 |                        5.68 |               5.68 | 250.00|250.00|500.00     | 특별배당 가능성|유동성 주의|Follower|배당 불안정|가치 함정 주의            |

## Notes
- `excluded=true` 는 최근 급등 규칙 때문에 밸류 버킷에서 제외된 종목입니다.
- `missing_data` 는 소스 부재 시 자동으로 붙는 플래그이며 파이프라인은 중단되지 않습니다.
- `Core missing fields` 는 가격/시총/PER/PBR/배당/3개년 실적처럼 핵심 판단 항목 기준입니다.
- 상단 추천은 최근 반복 노출, 업종 쏠림, 시총 쏠림을 완화한 `다변화 뷰` 기준입니다.
- `Special Dividend Watch` 는 최근 실제 배당수익률이 평년화 배당수익률보다 과도하게 높아 착시 가능성이 있는 종목입니다.