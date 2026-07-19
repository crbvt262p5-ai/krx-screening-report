import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as xlsx from "xlsx";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, "..");
const dataDir = path.join(rootDir, "data");

const portfolioPath = path.join(dataDir, "portfolio_positions.csv");
const screeningPath = path.join(dataDir, "latest.csv");

const OVERSEAS_TICKER_ALIASES = {
  "스미토모": ["8053.T"],
  "스미토모상사": ["8053.T"],
  "sumitomo": ["8053.T"],
  "sumitomo corporation": ["8053.T"],
  "도쿄카이죠홀딩스": ["8766.T"],
  "도쿄해상홀딩스": ["8766.T"],
  "tokio marine holdings": ["8766.T"],
};

const OVERSEAS_VALUATION_OVERRIDES = {
  NVDA: { per: 31.06, pbr: 25.13, eps: 6.53, forwardPer: 20.34 },
  AAPL: { per: 39.7, pbr: 45.11, eps: 8.25, forwardPer: 35.89 },
  META: { per: 21.94, pbr: 6.28, eps: 27.49, forwardPer: 18.37 },
  GOOGL: { per: 27.43, pbr: 9.1, eps: 13.11, forwardPer: 28.41 },
  TSM: { per: 26.3, pbr: 9.0, eps: 13.44, forwardPer: 18.55 },
  SIRI: { per: 12.92, pbr: 0.87, eps: 2.35, forwardPer: 9.53 },
  C: { per: 14.06, pbr: 1.13, eps: 9.2, forwardPer: 11.24 },
  NKE: { per: 20.37, pbr: 4.27, eps: 2.1, forwardPer: 25.04 },
  "스미토모": { per: 12.14, pbr: 1.52, eps: 124.67, forwardPer: 11.19 },
  "스미토모상사": { per: 12.14, pbr: 1.52, eps: 124.67, forwardPer: 11.19 },
  "도쿄카이죠홀딩스": { per: 27.84, pbr: 1.79, eps: 279.15, forwardPer: 16.08 },
};

const YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote";

function toCellString(value) {
  if (value === null || value === undefined) return "";
  return String(value).trim();
}

function parseNullableNumber(value) {
  const normalized = toCellString(value).replaceAll(",", "").replaceAll("%", "");
  if (!normalized || normalized.toLowerCase() === "nan") return null;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function roundMetric(value) {
  if (value === null || value === undefined || !Number.isFinite(value)) return null;
  return Math.round(value * 100) / 100;
}

function normalizeAliasKey(value) {
  return toCellString(value).toLowerCase().replaceAll(/\s+/g, " ");
}

function inferAssetClass(name, assetClass) {
  if (assetClass) return assetClass;
  if (/(KODEX|TIGER|KIWOOM|KoAct|KOACT|ETF)/.test(name)) return "ETF";
  return "주식";
}

function normalizePortfolioRows(records) {
  return records.map((record, index) => {
    const ticker = toCellString(record.ticker);
    const name = toCellString(record.name);
    const assetClass = inferAssetClass(name, toCellString(record.asset_class));
    return {
      rowId: `${ticker}-${name}-${index + 1}`,
      ticker,
      name,
      assetClass,
      per: parseNullableNumber(record.per),
      pbr: parseNullableNumber(record.pbr),
      eps: parseNullableNumber(record.eps),
      forwardPer: parseNullableNumber(record.forward_per),
    };
  });
}

function loadWorkbookRows(filePath) {
  return readFile(filePath).then((buffer) => {
    const workbook = xlsx.read(buffer, { type: "buffer" });
    const sheet = workbook.Sheets[workbook.SheetNames[0]];
    return xlsx.utils.sheet_to_json(sheet, { defval: "", raw: false });
  });
}

function buildScreeningLookup(records) {
  const byTicker = new Map();
  const byName = new Map();

  for (const record of records) {
    const prevClose = parseNullableNumber(record.prev_close);
    const per = parseNullableNumber(record.per);
    const pbr = parseNullableNumber(record.pbr);
    const consensusEpsEstimate = parseNullableNumber(record.consensus_eps_estimate);
    const growth = parseNullableNumber(record.forecast_growth_next_year_pct);
    const trailingEps = prevClose !== null && per !== null && per !== 0 ? prevClose / per : null;
    const derivedForwardEps =
      trailingEps !== null && growth !== null && growth > -80 && growth < 150
        ? trailingEps * (1 + growth / 100)
        : null;
    const resolvedEps = roundMetric(consensusEpsEstimate ?? trailingEps);
    const forwardBase = consensusEpsEstimate ?? derivedForwardEps ?? trailingEps;
    const forwardPer =
      prevClose !== null && forwardBase !== null && forwardBase !== 0 ? roundMetric(prevClose / forwardBase) : null;

    const mapped = {
      ticker: toCellString(record.ticker),
      name: toCellString(record.name),
      per: roundMetric(per),
      pbr: roundMetric(pbr),
      eps: resolvedEps,
      forwardPer,
    };

    if (mapped.ticker) byTicker.set(mapped.ticker, mapped);
    if (mapped.name) byName.set(mapped.name, mapped);
  }

  return { byTicker, byName };
}

function buildYahooCandidates(row) {
  const ticker = toCellString(row.ticker).toUpperCase();
  const aliasCandidates = [
    ...(OVERSEAS_TICKER_ALIASES[normalizeAliasKey(row.ticker)] ?? []),
    ...(OVERSEAS_TICKER_ALIASES[normalizeAliasKey(row.name)] ?? []),
  ];

  if (!ticker) return [...new Set(aliasCandidates)];
  if (/^\d{6}$/.test(ticker)) return [...new Set([`${ticker}.KS`, `${ticker}.KQ`, ...aliasCandidates])];
  if (/^[A-Z][A-Z0-9.\-=]{0,14}$/.test(ticker)) return [...new Set([ticker, ...aliasCandidates])];
  return [...new Set(aliasCandidates)];
}

function getValuationOverride(row) {
  const keys = [toCellString(row.ticker).toUpperCase(), toCellString(row.ticker), toCellString(row.name).toUpperCase(), toCellString(row.name)];
  for (const key of keys) {
    if (OVERSEAS_VALUATION_OVERRIDES[key]) {
      return OVERSEAS_VALUATION_OVERRIDES[key];
    }
  }
  return null;
}

async function fetchYahooQuotes(symbols) {
  if (symbols.length === 0) return new Map();
  const url = new URL(YAHOO_QUOTE_URL);
  url.searchParams.set("symbols", symbols.join(","));
  const response = await fetch(url, {
    headers: { "User-Agent": "Mozilla/5.0", Accept: "application/json" },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Yahoo quote failed: ${response.status}`);
  }
  const payload = await response.json();
  const results = payload?.quoteResponse?.result ?? [];
  return new Map(results.filter((item) => item?.symbol).map((item) => [item.symbol, item]));
}

function metricCount(quote) {
  if (!quote) return -1;
  const pbr =
    Number.isFinite(quote.priceToBook) ? quote.priceToBook
    : Number.isFinite(quote.bookValue) && Number.isFinite(quote.regularMarketPrice) && quote.bookValue !== 0
      ? quote.regularMarketPrice / quote.bookValue
      : null;
  return [quote.trailingPE, quote.forwardPE, pbr, quote.epsTrailingTwelveMonths, quote.epsCurrentYear]
    .filter((value) => Number.isFinite(value)).length;
}

function extractYahooMetrics(quote) {
  if (!quote) return { per: null, pbr: null, eps: null, forwardPer: null };
  const pbr =
    Number.isFinite(quote.priceToBook) ? quote.priceToBook
    : Number.isFinite(quote.bookValue) && Number.isFinite(quote.regularMarketPrice) && quote.bookValue !== 0
      ? quote.regularMarketPrice / quote.bookValue
      : null;
  const eps =
    Number.isFinite(quote.epsTrailingTwelveMonths) ? quote.epsTrailingTwelveMonths
    : Number.isFinite(quote.epsCurrentYear) ? quote.epsCurrentYear
    : Number.isFinite(quote.epsForward) ? quote.epsForward
    : null;
  const forwardPer =
    Number.isFinite(quote.forwardPE) ? quote.forwardPE
    : Number.isFinite(quote.epsCurrentYear) && Number.isFinite(quote.regularMarketPrice) && quote.epsCurrentYear !== 0
      ? quote.regularMarketPrice / quote.epsCurrentYear
      : null;
  return {
    per: roundMetric(Number.isFinite(quote.trailingPE) ? quote.trailingPE : null),
    pbr: roundMetric(pbr),
    eps: roundMetric(eps),
    forwardPer: roundMetric(forwardPer),
  };
}

async function main() {
  const [portfolioRecords, screeningRecords] = await Promise.all([
    loadWorkbookRows(portfolioPath),
    loadWorkbookRows(screeningPath),
  ]);

  const portfolioRows = normalizePortfolioRows(portfolioRecords);
  const screeningLookup = buildScreeningLookup(screeningRecords);

  const yahooCandidateMap = new Map();
  for (const row of portfolioRows) {
    if (row.assetClass === "ETF") continue;
    yahooCandidateMap.set(row.rowId, buildYahooCandidates(row));
  }

  const allSymbols = [...new Set([...yahooCandidateMap.values()].flat())];
  let yahooQuotes = new Map();
  try {
    yahooQuotes = await fetchYahooQuotes(allSymbols);
  } catch {
    yahooQuotes = new Map();
  }

  const report = portfolioRows.map((row) => {
    const screening = screeningLookup.byTicker.get(row.ticker) ?? screeningLookup.byName.get(row.name) ?? null;
    const override = getValuationOverride(row);
    const candidates = yahooCandidateMap.get(row.rowId) ?? [];
    const bestSymbol = [...candidates].sort((a, b) => metricCount(yahooQuotes.get(b)) - metricCount(yahooQuotes.get(a)))[0];
    const yahoo = extractYahooMetrics(yahooQuotes.get(bestSymbol));
    const resolved = {
      per: row.per ?? screening?.per ?? override?.per ?? yahoo.per ?? null,
      pbr: row.pbr ?? screening?.pbr ?? override?.pbr ?? yahoo.pbr ?? null,
      eps: row.eps ?? screening?.eps ?? override?.eps ?? yahoo.eps ?? null,
      forwardPer: row.forwardPer ?? screening?.forwardPer ?? override?.forwardPer ?? yahoo.forwardPer ?? null,
    };
    const missing = Object.entries(resolved)
      .filter(([, value]) => value === null)
      .map(([key]) => key);

    return {
      ticker: row.ticker,
      name: row.name,
      assetClass: row.assetClass,
      bestSymbol: bestSymbol ?? "",
      resolved,
      missing,
    };
  });

  const nonEtf = report.filter((row) => row.assetClass !== "ETF");
  const missingRows = nonEtf.filter((row) => row.missing.length > 0);

  console.log(`Non-ETF coverage: ${nonEtf.length - missingRows.length}/${nonEtf.length}`);
  if (missingRows.length === 0) {
    console.log("All non-ETF positions have PER/PBR/EPS/Fwd PER.");
    return;
  }

  console.log("Rows still missing valuation fields:");
  for (const row of missingRows) {
    console.log(
      [
        row.ticker,
        row.name,
        `symbol=${row.bestSymbol || "-"}`,
        `missing=${row.missing.join("/")}`,
        `per=${row.resolved.per ?? "-"}`,
        `pbr=${row.resolved.pbr ?? "-"}`,
        `eps=${row.resolved.eps ?? "-"}`,
        `fwd=${row.resolved.forwardPer ?? "-"}`,
      ].join(" | "),
    );
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
