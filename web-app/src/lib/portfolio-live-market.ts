import type { PortfolioPosition } from "@/lib/portfolio-dashboard";

type YahooQuote = {
  symbol?: string;
  currency?: string | null;
  regularMarketPrice?: number | null;
  regularMarketPreviousClose?: number | null;
  regularMarketChangePercent?: number | null;
};

export type PortfolioMarketSnapshot = {
  rowId: string;
  ticker: string;
  name: string;
  resolvedSymbol: string | null;
  currentPrice: number | null;
  previousClose: number | null;
  changePct: number | null;
  currency: string | null;
  fxRateToKrw: number | null;
  currentPriceKrw: number | null;
  quantity: number | null;
  estimatedHoldingValueKrw: number | null;
  estimatedDayPnlKrw: number | null;
};

const YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart";
const YAHOO_REQUEST_CONCURRENCY = 8;

const OVERSEAS_TICKER_ALIASES: Record<string, string[]> = {
  "kodex 고배당주": ["279530.KS"],
  "kiwoom 미국고배...": ["0107F0.KS"],
  "kiwoom 미국고배당&ai테크": ["0107F0.KS"],
  "koact k수출핵심...": ["0074K0.KS"],
  "koact k수출핵심기업top30": ["0074K0.KS"],
  "tiger 은행고배...": ["466940.KS"],
  "tiger 은행고배당플러스top10": ["466940.KS"],
  "tiger 지주회사": ["307520.KS"],
  "kodex 미국나스닥100": ["379810.KS"],
  "스미토모": ["8053.T"],
  "스미토모상사": ["8053.T"],
  "sumitomo": ["8053.T"],
  "sumitomo corporation": ["8053.T"],
  "도쿄카이죠홀딩스": ["8766.T"],
  "도쿄해상홀딩스": ["8766.T"],
  "tokio marine holdings": ["8766.T"],
};

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function roundMetric(value: number | null) {
  if (!isFiniteNumber(value)) {
    return null;
  }
  return Math.round(value * 100) / 100;
}

function normalizeAliasKey(value: string) {
  return value.trim().toLowerCase().replaceAll(/\s+/g, " ");
}

export function buildYahooCandidates(row: Pick<PortfolioPosition, "ticker" | "name">) {
  const ticker = row.ticker.trim().toUpperCase();
  const aliasCandidates = [
    ...(OVERSEAS_TICKER_ALIASES[normalizeAliasKey(row.ticker)] ?? []),
    ...(OVERSEAS_TICKER_ALIASES[normalizeAliasKey(row.name)] ?? []),
  ];

  if (!ticker) {
    return [...new Set(aliasCandidates)];
  }

  if (/^\d{6}$/.test(ticker)) {
    return [...new Set([`${ticker}.KS`, `${ticker}.KQ`, ...aliasCandidates])];
  }

  if (/^[A-Z][A-Z0-9.\-=]{0,14}$/.test(ticker)) {
    return [...new Set([ticker, ...aliasCandidates])];
  }

  return [...new Set(aliasCandidates)];
}

function metricCount(quote: YahooQuote | undefined) {
  if (!quote) {
    return -1;
  }

  return [quote.regularMarketPrice, quote.regularMarketPreviousClose, quote.regularMarketChangePercent].filter(isFiniteNumber).length;
}

async function fetchYahooChartQuote(symbol: string): Promise<YahooQuote | null> {
  const url = new URL(`${YAHOO_CHART_URL}/${encodeURIComponent(symbol)}`);
  url.searchParams.set("interval", "1d");
  url.searchParams.set("range", "5d");

  try {
    const response = await fetch(url, {
      headers: {
        "User-Agent": "Mozilla/5.0",
        Accept: "application/json",
      },
      cache: "no-store",
    });

    if (!response.ok) {
      return null;
    }

    const payload = (await response.json()) as {
      chart?: {
        result?: Array<{
          meta?: {
            symbol?: string;
            currency?: string | null;
            regularMarketPrice?: number | null;
            chartPreviousClose?: number | null;
          };
          indicators?: {
            quote?: Array<{ close?: Array<number | null> }>;
          };
        }>;
      };
    };
    const result = payload.chart?.result?.[0];
    const meta = result?.meta;
    if (!meta || !isFiniteNumber(meta.regularMarketPrice)) {
      return null;
    }

    const closes = (result.indicators?.quote?.[0]?.close ?? []).filter(isFiniteNumber);
    const previousClose = closes.length >= 2
      ? closes.at(-2) ?? null
      : isFiniteNumber(meta.chartPreviousClose)
        ? meta.chartPreviousClose
        : null;
    const changePct = previousClose && previousClose !== 0
      ? ((meta.regularMarketPrice - previousClose) / previousClose) * 100
      : null;

    return {
      symbol: meta.symbol ?? symbol,
      currency: meta.currency ?? null,
      regularMarketPrice: meta.regularMarketPrice,
      regularMarketPreviousClose: previousClose,
      regularMarketChangePercent: changePct,
    };
  } catch {
    return null;
  }
}

async function fetchYahooQuotes(symbols: string[]) {
  const uniqueSymbols = [...new Set(symbols)];
  const quotes = new Map<string, YahooQuote>();
  let cursor = 0;

  async function worker() {
    while (cursor < uniqueSymbols.length) {
      const symbol = uniqueSymbols[cursor];
      cursor += 1;
      const quote = await fetchYahooChartQuote(symbol);
      if (quote) {
        quotes.set(symbol, quote);
      }
    }
  }

  await Promise.all(
    Array.from(
      { length: Math.min(YAHOO_REQUEST_CONCURRENCY, uniqueSymbols.length) },
      () => worker(),
    ),
  );
  return quotes;
}

function parseShareCount(notes: string) {
  const matched = notes.replaceAll(",", "").match(/(\d+)\s*주/);
  if (!matched) {
    return null;
  }
  const parsed = Number(matched[1]);
  return Number.isFinite(parsed) ? parsed : null;
}

function resolveFxRateToKrw(currency: string | null | undefined, fxQuotes: Map<string, YahooQuote>) {
  if (!currency || currency === "KRW") {
    return 1;
  }
  if (currency === "USD") {
    return roundMetric(fxQuotes.get("KRW=X")?.regularMarketPrice ?? null);
  }
  if (currency === "JPY") {
    return roundMetric(fxQuotes.get("JPYKRW=X")?.regularMarketPrice ?? null);
  }
  return null;
}

export async function loadPortfolioMarketSnapshots(rows: PortfolioPosition[]) {
  const candidateMap = new Map<string, string[]>();

  for (const row of rows) {
    candidateMap.set(row.rowId, buildYahooCandidates(row));
  }

  const marketSymbols = [...new Set([...candidateMap.values()].flat())];
  const fxSymbols = ["KRW=X", "JPYKRW=X"];
  const quotes = await fetchYahooQuotes([...new Set([...marketSymbols, ...fxSymbols])]);
  const fxQuotes = new Map(
    fxSymbols.flatMap((symbol) => {
      const quote = quotes.get(symbol);
      return quote ? [[symbol, quote] as const] : [];
    }),
  );

  return rows.map<PortfolioMarketSnapshot>((row) => {
    const candidates = candidateMap.get(row.rowId) ?? [];
    const resolvedSymbol = [...candidates].sort((left, right) => metricCount(quotes.get(right)) - metricCount(quotes.get(left)))[0] ?? null;
    const quote = resolvedSymbol ? quotes.get(resolvedSymbol) : undefined;
    const currentPrice = roundMetric(isFiniteNumber(quote?.regularMarketPrice) ? quote.regularMarketPrice : null);
    const previousClose = roundMetric(isFiniteNumber(quote?.regularMarketPreviousClose) ? quote.regularMarketPreviousClose : null);
    const changePct = roundMetric(isFiniteNumber(quote?.regularMarketChangePercent) ? quote.regularMarketChangePercent : null);
    const currency = quote?.currency ?? (row.marketScope === "국내" ? "KRW" : null);
    const fxRateToKrw = resolveFxRateToKrw(currency, fxQuotes);
    const currentPriceKrw =
      currentPrice !== null && fxRateToKrw !== null ? roundMetric(currentPrice * fxRateToKrw) : null;
    const quantity = parseShareCount(row.notes);
    const estimatedHoldingValueKrw =
      currentPriceKrw !== null && quantity !== null ? roundMetric(currentPriceKrw * quantity) : null;
    const estimatedDayPnlKrw =
      currentPrice !== null && previousClose !== null && fxRateToKrw !== null && quantity !== null
        ? roundMetric((currentPrice - previousClose) * fxRateToKrw * quantity)
        : null;

    return {
      rowId: row.rowId,
      ticker: row.ticker,
      name: row.name,
      resolvedSymbol,
      currentPrice,
      previousClose,
      changePct,
      currency,
      fxRateToKrw,
      currentPriceKrw,
      quantity,
      estimatedHoldingValueKrw,
      estimatedDayPnlKrw,
    };
  });
}
