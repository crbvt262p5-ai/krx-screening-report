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

const YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote";

const OVERSEAS_TICKER_ALIASES: Record<string, string[]> = {
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

async function fetchYahooQuotes(symbols: string[]) {
  if (symbols.length === 0) {
    return new Map<string, YahooQuote>();
  }

  const url = new URL(YAHOO_QUOTE_URL);
  url.searchParams.set("symbols", symbols.join(","));

  const response = await fetch(url, {
    headers: {
      "User-Agent": "Mozilla/5.0",
      Accept: "application/json",
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Yahoo 시세 조회 실패 (${response.status})`);
  }

  const payload = (await response.json()) as {
    quoteResponse?: {
      result?: YahooQuote[];
    };
  };

  const results = payload.quoteResponse?.result ?? [];
  return new Map(
    results
      .filter((item) => typeof item.symbol === "string" && item.symbol.length > 0)
      .map((item) => [item.symbol as string, item]),
  );
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
