import type { PortfolioPosition } from "@/lib/portfolio-dashboard";

type YahooQuote = {
  symbol?: string;
  trailingPE?: number | null;
  forwardPE?: number | null;
  priceToBook?: number | null;
  bookValue?: number | null;
  regularMarketPrice?: number | null;
  epsTrailingTwelveMonths?: number | null;
  epsCurrentYear?: number | null;
  epsForward?: number | null;
};

type EnrichmentStatus = "updated" | "unchanged" | "skipped" | "unresolved";

export type ValuationEnrichmentItem = {
  rowId: string;
  ticker: string;
  name: string;
  status: EnrichmentStatus;
  source: string | null;
  reason: string | null;
};

export type ValuationEnrichmentResponse = {
  rows: PortfolioPosition[];
  items: ValuationEnrichmentItem[];
  summary: {
    updatedCount: number;
    unchangedCount: number;
    skippedCount: number;
    unresolvedCount: number;
  };
};

const YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote";

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function roundMetric(value: number | null) {
  if (!isFiniteNumber(value)) {
    return null;
  }
  return Math.round(value * 100) / 100;
}

function buildYahooCandidates(row: PortfolioPosition) {
  const ticker = row.ticker.trim().toUpperCase();

  if (!ticker) {
    return [];
  }

  if (/^\d{6}$/.test(ticker)) {
    return [`${ticker}.KS`, `${ticker}.KQ`];
  }

  if (/^[A-Z][A-Z0-9.\-=]{0,14}$/.test(ticker)) {
    return [ticker];
  }

  return [];
}

function metricCount(quote: YahooQuote | undefined) {
  if (!quote) {
    return -1;
  }

  const pbr =
    isFiniteNumber(quote.priceToBook)
      ? quote.priceToBook
      : isFiniteNumber(quote.bookValue) && isFiniteNumber(quote.regularMarketPrice) && quote.bookValue !== 0
        ? quote.regularMarketPrice / quote.bookValue
        : null;

  return [quote.trailingPE, quote.forwardPE, pbr, quote.epsTrailingTwelveMonths, quote.epsCurrentYear]
    .filter(isFiniteNumber)
    .length;
}

function extractMetrics(quote: YahooQuote | undefined) {
  if (!quote) {
    return {
      per: null,
      pbr: null,
      eps: null,
      forwardPer: null,
    };
  }

  const pbr =
    isFiniteNumber(quote.priceToBook)
      ? quote.priceToBook
      : isFiniteNumber(quote.bookValue) && isFiniteNumber(quote.regularMarketPrice) && quote.bookValue !== 0
        ? quote.regularMarketPrice / quote.bookValue
        : null;

  return {
    per: roundMetric(isFiniteNumber(quote.trailingPE) ? quote.trailingPE : null),
    pbr: roundMetric(pbr),
    eps: roundMetric(
      isFiniteNumber(quote.epsTrailingTwelveMonths)
        ? quote.epsTrailingTwelveMonths
        : isFiniteNumber(quote.epsCurrentYear)
          ? quote.epsCurrentYear
          : isFiniteNumber(quote.epsForward)
            ? quote.epsForward
            : null,
    ),
    forwardPer: roundMetric(
      isFiniteNumber(quote.forwardPE)
        ? quote.forwardPE
        : isFiniteNumber(quote.epsCurrentYear) && isFiniteNumber(quote.regularMarketPrice) && quote.epsCurrentYear !== 0
          ? quote.regularMarketPrice / quote.epsCurrentYear
          : null,
    ),
  };
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

export async function enrichPortfolioRows(rows: PortfolioPosition[]): Promise<ValuationEnrichmentResponse> {
  const candidateMap = new Map<string, string[]>();

  for (const row of rows) {
    candidateMap.set(row.rowId, buildYahooCandidates(row));
  }

  const symbols = [...new Set([...candidateMap.values()].flat())];
  const quotes = await fetchYahooQuotes(symbols);

  const items: ValuationEnrichmentItem[] = [];
  const nextRows = rows.map((row) => {
    if (row.assetClass === "ETF") {
      items.push({
        rowId: row.rowId,
        ticker: row.ticker,
        name: row.name,
        status: "skipped",
        source: null,
        reason: "ETF는 개별 기업 밸류 지표보다 지수 구성과 분배금 성격이 더 중요합니다.",
      });
      return row;
    }

    const candidates = candidateMap.get(row.rowId) ?? [];
    if (candidates.length === 0) {
      items.push({
        rowId: row.rowId,
        ticker: row.ticker,
        name: row.name,
        status: "unresolved",
        source: null,
        reason: "조회 가능한 티커 형식이 아니어서 자동 연결이 어렵습니다.",
      });
      return row;
    }

    const bestSymbol = [...candidates].sort((left, right) => metricCount(quotes.get(right)) - metricCount(quotes.get(left)))[0];
    const quote = quotes.get(bestSymbol);
    const metrics = extractMetrics(quote);

    if ([metrics.per, metrics.pbr, metrics.eps, metrics.forwardPer].every((value) => value === null)) {
      items.push({
        rowId: row.rowId,
        ticker: row.ticker,
        name: row.name,
        status: "unresolved",
        source: bestSymbol ?? null,
        reason: "데이터 소스에서 유효한 밸류 지표를 찾지 못했습니다.",
      });
      return row;
    }

    const mergedRow = {
      ...row,
      per: metrics.per ?? row.per,
      pbr: metrics.pbr ?? row.pbr,
      eps: metrics.eps ?? row.eps,
      forwardPer: metrics.forwardPer ?? row.forwardPer,
    };

    const changed =
      mergedRow.per !== row.per ||
      mergedRow.pbr !== row.pbr ||
      mergedRow.eps !== row.eps ||
      mergedRow.forwardPer !== row.forwardPer;

    items.push({
      rowId: row.rowId,
      ticker: row.ticker,
      name: row.name,
      status: changed ? "updated" : "unchanged",
      source: bestSymbol ?? null,
      reason: changed ? null : "기존 값과 동일해 화면 숫자는 유지됩니다.",
    });

    return mergedRow;
  });

  return {
    rows: nextRows,
    items,
    summary: {
      updatedCount: items.filter((item) => item.status === "updated").length,
      unchangedCount: items.filter((item) => item.status === "unchanged").length,
      skippedCount: items.filter((item) => item.status === "skipped").length,
      unresolvedCount: items.filter((item) => item.status === "unresolved").length,
    },
  };
}
