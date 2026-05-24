# Playground Projects

이 저장소에는 여러 실험용 프로젝트가 들어 있지만, 현재 메인 자동화 대상은 한국 주식 스크리닝 파이프라인입니다.

## Main Project: KRX Automated Screening

KOSPI/KOSDAQ 전체 종목을 장 마감 후 자동으로 수집하고, Value bucket과 Growth early bucket 리포트를 생성합니다.

- 로컬 실행
- macOS `launchd` 자동 실행
- GitHub Actions 클라우드 실행
- GitHub Pages 모바일 대시보드 배포
- Telegram 링크/요약 알림

자세한 설치와 운영 문서는 아래를 보면 됩니다.

- [KRX Screening README](krx_screening/README.md)

핵심 경로:

- 코드: `krx_screening/`
- 실행 스크립트: `run_krx_screening.sh`
- 클라우드 워크플로: `.github/workflows/krx-pages.yml`
- Pages 빌더: `scripts/build_pages_site.py`
- Telegram 알림: `scripts/send_krx_telegram.py`

## Other Project

Telegram 채널 요약 MVP도 함께 들어 있습니다.

- 코드: `telegram_digest/`
