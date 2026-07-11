from __future__ import annotations

from datetime import datetime

from .config import Settings
from .logging_utils import setup_logging
from .reporting import write_outputs
from .scoring import score_equities
from .sources.finance import FinanceEnricher
from .sources.market import enrich_with_price_history, load_market_bundle
from .sources.news import NewsEnricher


def run_screening() -> tuple[str, str]:
    settings = Settings.load()
    logger = setup_logging(settings)
    today = datetime.now(settings.timezone).date()

    logger.info("Starting KRX screening pipeline")
    if settings.dart_enabled and settings.dart_api_key:
        logger.info("DART API key detected; DART-first finance enrichment enabled")
    elif settings.dart_enabled and not settings.dart_api_key:
        logger.warning("KRX_USE_DART is enabled but DART_API_KEY is missing; public fallbacks only")
    else:
        logger.info("Stable mode enabled; finance enrichment will rely on public fallbacks")
    market_bundle = load_market_bundle(today, logger)
    logger.info("Loaded %s equities", len(market_bundle.equities))

    enrich_with_price_history(market_bundle.equities, market_bundle.trading_date, logger)
    logger.info("Price history enrichment finished")

    finance_enricher = FinanceEnricher(settings, logger)
    finance_enricher.enrich(market_bundle.equities, market_bundle.trading_date)
    logger.info("Finance enrichment finished")

    news_enricher = NewsEnricher(settings, logger)
    news_enricher.enrich_growth_candidates(market_bundle.equities)
    logger.info("News enrichment finished")

    score_equities(market_bundle.equities)
    md_path, csv_path, latest_updated = write_outputs(
        settings,
        market_bundle.trading_date,
        market_bundle.equities,
    )
    logger.info("Outputs written: %s and %s", md_path, csv_path)
    if latest_updated:
        logger.info("Latest outputs updated")
    else:
        logger.warning("Latest outputs preserved because this run failed health checks")
    return md_path, csv_path
