from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from ..models import EquitySnapshot

try:
    from pykrx import stock as pykrx_stock
except ImportError:  # pragma: no cover
    pykrx_stock = None

try:
    import FinanceDataReader as fdr
except ImportError:  # pragma: no cover
    fdr = None


@dataclass
class MarketDataBundle:
    trading_date: date
    equities: list[EquitySnapshot]


def load_market_bundle(target_date: date, logger: logging.Logger) -> MarketDataBundle:
    trading_date = resolve_latest_trading_date(target_date, logger)
    logger.info("Using trading date %s", trading_date.isoformat())

    listings = []
    listing_details: dict[str, dict[str, float | None]] = {}
    for market in ("KOSPI", "KOSDAQ"):
        market_listings, detail_map = _load_market_listing(market, logger)
        listings.extend(market_listings)
        listing_details.update(detail_map)

    price_frames = {}
    cap_frames = {}
    fundamental_frames = {}
    date_str = trading_date.strftime("%Y%m%d")
    for market in ("KOSPI", "KOSDAQ"):
        price_frames[market] = _load_price_frame(date_str, market, logger)
        cap_frames[market] = _load_cap_frame(date_str, market, logger)
        fundamental_frames[market] = _load_fundamental_frame(date_str, market, logger)

    equities: list[EquitySnapshot] = []
    for item in listings:
        snapshot = EquitySnapshot(ticker=item["ticker"], market=item["market"], name=item["name"])
        price_row = _safe_row(price_frames.get(snapshot.market), snapshot.ticker)
        cap_row = _safe_row(cap_frames.get(snapshot.market), snapshot.ticker)
        fund_row = _safe_row(fundamental_frames.get(snapshot.market), snapshot.ticker)
        listing_detail = listing_details.get(snapshot.ticker, {})
        snapshot.sector = _coerce_text(listing_detail.get("sector"))
        snapshot.industry = _coerce_text(listing_detail.get("industry"))

        snapshot.close = _coerce_float(price_row.get("종가")) or _coerce_float(listing_detail.get("close"))
        snapshot.market_cap = _coerce_float(cap_row.get("시가총액")) or _coerce_float(
            listing_detail.get("market_cap")
        )
        snapshot.size_bucket = _classify_size_bucket(snapshot.market_cap)
        snapshot.per = _coerce_float(fund_row.get("PER")) or _coerce_float(listing_detail.get("per"))
        snapshot.pbr = _coerce_float(fund_row.get("PBR")) or _coerce_float(listing_detail.get("pbr"))
        snapshot.dividend_yield = _coerce_float(fund_row.get("DIV")) or _coerce_float(
            listing_detail.get("dividend_yield")
        )
        if snapshot.dividend_yield is not None:
            snapshot.dividend_yield_trailing = _coerce_float(listing_detail.get("dividend_yield_trailing"))
            snapshot.dividend_yield_normalized = _coerce_float(listing_detail.get("dividend_yield_normalized"))
            snapshot.dividend_yield_source = _coerce_text(listing_detail.get("dividend_yield_source"))
            if snapshot.dividend_yield_trailing is None:
                snapshot.dividend_yield_trailing = snapshot.dividend_yield
            if snapshot.dividend_yield_normalized is None:
                snapshot.dividend_yield_normalized = snapshot.dividend_yield
            if snapshot.dividend_yield_source is None:
                snapshot.dividend_yield_source = "pykrx_snapshot"

        if snapshot.close is None:
            snapshot.mark_missing("prev_close")
        if snapshot.market_cap is None:
            snapshot.mark_missing("market_cap")
        if snapshot.per is None:
            snapshot.mark_missing("per")
        if snapshot.pbr is None:
            snapshot.mark_missing("pbr")
        if snapshot.dividend_yield is None:
            snapshot.mark_missing("dividend_yield")

        equities.append(snapshot)

    _enrich_with_investor_flows(equities, trading_date, logger)

    return MarketDataBundle(trading_date=trading_date, equities=equities)


def resolve_latest_trading_date(target_date: date, logger: logging.Logger) -> date:
    if pykrx_stock is None and fdr is None:
        raise RuntimeError("pykrx or FinanceDataReader is required to resolve trading dates.")

    for offset in range(0, 10):
        candidate = target_date - timedelta(days=offset)
        if _has_market_data(candidate.strftime("%Y%m%d"), logger):
            return candidate
    raise RuntimeError("Could not resolve a recent KRX trading date.")


def enrich_with_price_history(
    equities: list[EquitySnapshot], trading_date: date, logger: logging.Logger
) -> None:
    start_date = trading_date - timedelta(days=430)
    for equity in equities:
        hist = _load_price_history(equity.ticker, start_date, trading_date, logger)
        if hist.empty or "Close" not in hist.columns:
            equity.mark_missing("price_history")
            continue

        close_series = hist["Close"].dropna()
        if close_series.empty:
            equity.mark_missing("price_history")
            continue

        latest_close = close_series.iloc[-1]
        if not latest_close:
            equity.mark_missing("price_history")
            continue

        equity.returns_1m = _return_over_days(close_series, 21)
        equity.returns_3m = _return_over_days(close_series, 63)
        equity.returns_6m = _return_over_days(close_series, 126)
        equity.returns_12m = _return_over_days(close_series, 252)
        rolling_high = close_series.tail(252).max()
        equity.high_52w_ratio = round((latest_close / rolling_high) * 100, 2) if rolling_high else None
        equity.ma_20 = _moving_average(close_series, 20)
        equity.ma_60 = _moving_average(close_series, 60)
        equity.ma_120 = _moving_average(close_series, 120)
        equity.avg_trading_value_20d = _average_trading_value(hist, 20)
        equity.avg_trading_value_60d = _average_trading_value(hist, 60)

        if equity.returns_1m is None:
            equity.mark_missing("returns_1m")
        if equity.returns_3m is None:
            equity.mark_missing("returns_3m")
        if equity.returns_6m is None:
            equity.mark_missing("returns_6m")
        if equity.returns_12m is None:
            equity.mark_missing("returns_12m")
        if equity.high_52w_ratio is None:
            equity.mark_missing("high_52w_ratio")
        if equity.ma_20 is None:
            equity.mark_missing("ma_20")
        if equity.ma_60 is None:
            equity.mark_missing("ma_60")
        if equity.ma_120 is None:
            equity.mark_missing("ma_120")
        if equity.avg_trading_value_20d is None:
            equity.mark_missing("avg_trading_value_20d")
        if equity.avg_trading_value_60d is None:
            equity.mark_missing("avg_trading_value_60d")


def _load_market_listing(
    market: str, logger: logging.Logger
) -> tuple[list[dict[str, str]], dict[str, dict[str, object]]]:
    if pykrx_stock is not None:
        try:
            tickers = pykrx_stock.get_market_ticker_list(market=market)
            listings = [
                {
                    "ticker": ticker,
                    "name": pykrx_stock.get_market_ticker_name(ticker),
                    "market": market,
                }
                for ticker in tickers
            ]
            return listings, {}
        except Exception as exc:  # pragma: no cover
            logger.warning("pykrx listing failed for %s: %s", market, exc)

    if fdr is not None:
        try:
            listing = fdr.StockListing(market)
            listings = [
                {"ticker": str(row.Code).zfill(6), "name": row.Name, "market": market}
                for row in listing.itertuples()
            ]
            detail_map = {
                str(row.Code).zfill(6): {
                    "close": _coerce_float(getattr(row, "Close", None)),
                    "market_cap": _coerce_float(getattr(row, "Marcap", None)),
                    "sector": _first_present_text(row, "Sector", "업종", "WICS업종명"),
                    "industry": _first_present_text(row, "Industry", "산업", "업종소"),
                }
                for row in listing.itertuples()
            }
            return listings, detail_map
        except Exception as exc:  # pragma: no cover
            logger.warning("FinanceDataReader listing failed for %s: %s", market, exc)

    cached_listings, cached_detail_map = _load_cached_market_listing(market, logger)
    if cached_listings:
        logger.warning(
            "Using cached historical universe for %s because live listing sources are unavailable",
            market,
        )
        return cached_listings, cached_detail_map

    logger.error("No market listing source available for %s", market)
    return [], {}


def _has_market_data(date_str: str, logger: logging.Logger) -> bool:
    if pykrx_stock is not None:
        try:
            frame = pykrx_stock.get_market_ohlcv_by_ticker(date_str, market="KOSPI")
            return not frame.empty
        except Exception as exc:  # pragma: no cover
            logger.warning("pykrx trading date probe failed for %s: %s", date_str, exc)

    if fdr is not None:
        try:
            frame = fdr.DataReader("KS11", date_str, date_str)
            return not frame.empty
        except Exception as exc:  # pragma: no cover
            logger.warning("Trading date probe failed for %s: %s", date_str, exc)
            return False

    return False


def _load_price_frame(date_str: str, market: str, logger: logging.Logger) -> pd.DataFrame:
    if pykrx_stock is not None:
        try:
            return pykrx_stock.get_market_ohlcv_by_ticker(date_str, market=market)
        except Exception as exc:  # pragma: no cover
            logger.warning("pykrx price snapshot failed for %s on %s: %s", market, date_str, exc)
    logger.warning("pykrx unavailable, price snapshot for %s may be incomplete", market)
    return pd.DataFrame()


def _load_cap_frame(date_str: str, market: str, logger: logging.Logger) -> pd.DataFrame:
    if pykrx_stock is not None:
        try:
            return pykrx_stock.get_market_cap_by_ticker(date_str, market=market)
        except Exception as exc:  # pragma: no cover
            logger.warning("pykrx market cap snapshot failed for %s on %s: %s", market, date_str, exc)
    logger.warning("pykrx unavailable, market cap snapshot for %s may be incomplete", market)
    return pd.DataFrame()


def _load_fundamental_frame(date_str: str, market: str, logger: logging.Logger) -> pd.DataFrame:
    if pykrx_stock is not None:
        try:
            return pykrx_stock.get_market_fundamental_by_ticker(date_str, market=market)
        except Exception as exc:  # pragma: no cover
            logger.warning("pykrx fundamentals snapshot failed for %s on %s: %s", market, date_str, exc)
    logger.warning("pykrx unavailable, fundamentals snapshot for %s may be incomplete", market)
    return pd.DataFrame()


def _load_price_history(ticker: str, start_date: date, end_date: date, logger: logging.Logger) -> pd.DataFrame:
    if pykrx_stock is not None:
        try:
            frame = pykrx_stock.get_market_ohlcv_by_date(
                start_date.strftime("%Y%m%d"),
                end_date.strftime("%Y%m%d"),
                ticker,
            )
            if not frame.empty and "종가" in frame.columns:
                return frame.rename(columns={"종가": "Close", "거래량": "Volume"})
        except Exception as exc:  # pragma: no cover
            logger.warning("pykrx price history failed for %s: %s", ticker, exc)

    if fdr is not None:
        try:
            frame = fdr.DataReader(ticker, start_date, end_date)
            if not frame.empty:
                return frame
        except Exception as exc:  # pragma: no cover
            logger.warning("FinanceDataReader price history failed for %s: %s", ticker, exc)

    return pd.DataFrame()


def _enrich_with_investor_flows(
    equities: list[EquitySnapshot], trading_date: date, logger: logging.Logger
) -> None:
    if pykrx_stock is None:
        for equity in equities:
            equity.mark_missing("investor_flow_3m", "etf_inclusion_change_3m")
        return

    start_date = trading_date - timedelta(days=92)
    flow_maps = {
        "외국인": {},
        "연기금": {},
    }
    for market in ("KOSPI", "KOSDAQ"):
        for investor in ("외국인", "연기금"):
            try:
                frame = pykrx_stock.get_market_net_purchases_of_equities_by_ticker(
                    start_date.strftime("%Y%m%d"),
                    trading_date.strftime("%Y%m%d"),
                    market=market,
                    investor=investor,
                )
            except Exception as exc:  # pragma: no cover
                logger.warning(
                    "pykrx investor flow failed for %s %s: %s",
                    market,
                    investor,
                    exc,
                )
                continue
            if frame is None or frame.empty:
                continue
            net_col = _find_net_buy_column(frame)
            if net_col is None:
                continue
            for ticker, value in frame[net_col].items():
                flow_maps[investor][str(ticker).zfill(6)] = _coerce_float(value)

    for equity in equities:
        equity.foreign_net_buy_3m = flow_maps["외국인"].get(equity.ticker)
        equity.pension_net_buy_3m = flow_maps["연기금"].get(equity.ticker)
        if equity.market_cap not in (None, 0):
            if equity.foreign_net_buy_3m is not None:
                equity.foreign_net_buy_ratio_3m = round(
                    (equity.foreign_net_buy_3m / equity.market_cap) * 100,
                    4,
                )
            if equity.pension_net_buy_3m is not None:
                equity.pension_net_buy_ratio_3m = round(
                    (equity.pension_net_buy_3m / equity.market_cap) * 100,
                    4,
                )
            combined = sum(
                value for value in (equity.foreign_net_buy_3m, equity.pension_net_buy_3m) if value is not None
            )
            if combined:
                equity.net_buy_ratio_3m = round((combined / equity.market_cap) * 100, 4)
        if equity.net_buy_ratio_3m is None:
            equity.mark_missing("investor_flow_3m")
        else:
            equity.clear_missing("investor_flow_3m")
        equity.mark_missing("etf_inclusion_change_3m")


def _return_over_days(close_series: pd.Series, periods: int) -> float | None:
    if len(close_series) <= periods:
        return None
    previous = close_series.iloc[-periods - 1]
    latest = close_series.iloc[-1]
    if previous in (None, 0):
        return None
    return round(((latest / previous) - 1) * 100, 2)


def _average_trading_value(frame: pd.DataFrame, periods: int) -> float | None:
    if frame.empty or "Close" not in frame.columns or "Volume" not in frame.columns:
        return None
    window = frame[["Close", "Volume"]].dropna().tail(periods)
    if len(window) < min(periods, 10):
        return None
    traded = pd.to_numeric(window["Close"], errors="coerce") * pd.to_numeric(
        window["Volume"], errors="coerce"
    )
    traded = traded.dropna()
    if traded.empty:
        return None
    return round(float(traded.mean()), 2)


def _moving_average(close_series: pd.Series, periods: int) -> float | None:
    window = close_series.dropna().tail(periods)
    if len(window) < min(periods, 15):
        return None
    return round(float(window.mean()), 2)


def _find_net_buy_column(frame: pd.DataFrame) -> str | None:
    for candidate in ("순매수거래대금", "순매수대금", "순매수"):
        if candidate in frame.columns:
            return candidate
    return None


def _load_cached_market_listing(
    market: str,
    logger: logging.Logger,
) -> tuple[list[dict[str, str]], dict[str, dict[str, object]]]:
    data_dir = Path.cwd() / "data"
    for path in sorted(data_dir.glob("screened_*.csv"), reverse=True):
        try:
            frame = pd.read_csv(path, dtype={"ticker": str}, encoding="utf-8-sig")
        except Exception:
            continue
        if len(frame) < 1000:
            continue
        if "market" not in frame.columns or "name" not in frame.columns:
            continue
        filtered = frame[frame["market"].astype(str) == market].copy()
        if filtered.empty:
            continue
        filtered["ticker"] = filtered["ticker"].astype(str).str.zfill(6)
        listings = [
            {"ticker": row.ticker, "name": str(row.name), "market": market}
            for row in filtered[["ticker", "name"]].drop_duplicates().itertuples(index=False)
        ]
        detail_map = {
            str(row.ticker): {
                "close": _coerce_float(getattr(row, "prev_close", None)),
                "market_cap": _coerce_float(getattr(row, "market_cap", None)),
                "per": _coerce_float(getattr(row, "per", None)),
                "pbr": _coerce_float(getattr(row, "pbr", None)),
                "dividend_yield": _coerce_float(getattr(row, "dividend_yield", None)),
                "dividend_yield_trailing": _coerce_float(getattr(row, "dividend_yield_trailing", None)),
                "dividend_yield_normalized": _coerce_float(getattr(row, "dividend_yield_normalized", None)),
                "dividend_yield_source": _coerce_text(getattr(row, "dividend_yield_source", None)),
                "sector": _coerce_text(getattr(row, "sector", None)),
                "industry": _coerce_text(getattr(row, "industry", None)),
            }
            for row in filtered[
                [
                    "ticker",
                    "prev_close",
                    "market_cap",
                    "per",
                    "pbr",
                    "dividend_yield",
                    "dividend_yield_trailing",
                    "dividend_yield_normalized",
                    "dividend_yield_source",
                    "sector",
                    "industry",
                ]
            ]
            .drop_duplicates(subset=["ticker"])
            .itertuples(index=False)
        }
        logger.info("Loaded cached universe from %s for %s", path.name, market)
        return listings, detail_map
    return [], {}


def _safe_row(frame: pd.DataFrame | None, ticker: str) -> pd.Series:
    if frame is None or frame.empty or ticker not in frame.index:
        return pd.Series(dtype="object")
    return frame.loc[ticker]


def _coerce_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_text(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text if text else None


def _first_present_text(row: object, *names: str) -> str | None:
    for name in names:
        value = getattr(row, name, None)
        text = _coerce_text(value)
        if text:
            return text
    return None


def _classify_size_bucket(market_cap: float | None) -> str | None:
    if market_cap is None:
        return None
    if market_cap >= 10_000_000_000_000:
        return "Mega"
    if market_cap >= 2_000_000_000_000:
        return "Large"
    if market_cap >= 300_000_000_000:
        return "Mid"
    return "Small"
