export type PortfolioPosition = {
  rowId: string;
  ticker: string;
  name: string;
  marketScope: string;
  assetClass: string;
  country: string;
  theme: string;
  themeCategory: string;
  subTheme: string;
  strategy: string;
  styleBucket: string;
  trendView: string;
  cycleView: string;
  conviction: string;
  fxExposure: string;
  timingView: string;
  actualWeightPct: number;
  targetWeightPct: number;
  per: number | null;
  pbr: number | null;
  eps: number | null;
  forwardPer: number | null;
  plannedAction: string;
  notes: string;
};

type RawRecord = Record<string, unknown>;

function looksLikeMojibake(value: string) {
  return /[ÃÂÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]/.test(value);
}

function repairMojibake(value: string) {
  if (!value || !looksLikeMojibake(value)) {
    return value;
  }

  try {
    const bytes = Uint8Array.from(value, (char) => char.charCodeAt(0) & 0xff);
    return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch {
    return value;
  }
}

const FIELD_ALIASES: Record<Exclude<keyof PortfolioPosition, "rowId">, string[]> = {
  ticker: ["ticker", "티커", "종목코드"],
  name: ["name", "종목명"],
  marketScope: ["market_scope", "marketScope", "국내해외", "시장구분"],
  assetClass: ["asset_class", "assetClass", "자산구분", "자산"],
  country: ["country", "국가"],
  theme: ["theme", "테마"],
  themeCategory: ["theme_category", "themeCategory", "테마종류", "테마분류"],
  subTheme: ["sub_theme", "subTheme", "세부테마", "서브테마"],
  strategy: ["strategy", "전략"],
  styleBucket: ["style_bucket", "styleBucket", "스타일"],
  trendView: ["trend_view", "trendView", "추세"],
  cycleView: ["cycle_view", "cycleView", "사이클"],
  conviction: ["conviction", "확신도"],
  fxExposure: ["fx_exposure", "fxExposure", "환노출"],
  timingView: ["timing_view", "timingView", "매수타이밍", "타이밍"],
  actualWeightPct: ["actual_weight_pct", "actualWeightPct", "actual_weight", "실제비중", "비중"],
  targetWeightPct: ["target_weight_pct", "targetWeightPct", "target_weight", "목표비중"],
  per: ["per", "PER"],
  pbr: ["pbr", "PBR"],
  eps: ["eps", "EPS"],
  forwardPer: ["forward_per", "forwardPer", "forwardPER", "포워드PER", "선행PER"],
  plannedAction: ["planned_action", "plannedAction", "액션", "운영액션"],
  notes: ["notes", "메모", "노트"],
};

function toCellString(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }

  return repairMojibake(String(value).trim());
}

function parseNumber(value: unknown): number {
  const normalized = toCellString(value).replaceAll(",", "").replaceAll("%", "");
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : 0;
}

function parseNullableNumber(value: unknown): number | null {
  const normalized = toCellString(value).replaceAll(",", "").replaceAll("%", "");
  if (!normalized) {
    return null;
  }
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function readField(record: RawRecord, aliases: string[]): unknown {
  for (const alias of aliases) {
    if (alias in record) {
      return record[alias];
    }
  }
  return "";
}

function inferMarketScope(ticker: string, assetClass: string, marketScope: string): string {
  if (marketScope) {
    return marketScope;
  }
  if (assetClass === "ETF" && /^(KODEX|TIGER|KIWOOM|KoAct|KOACT)/.test(ticker)) {
    return "국내";
  }
  if (/^\d{6}$/.test(ticker)) {
    return "국내";
  }
  return "해외";
}

function inferAssetClass(name: string, assetClass: string): string {
  if (assetClass) {
    return assetClass;
  }
  if (/(KODEX|TIGER|KIWOOM|KoAct|KOACT|ETF)/.test(name)) {
    return "ETF";
  }
  return "주식";
}

function inferCountry(marketScope: string, ticker: string, country: string): string {
  if (country) {
    return country;
  }
  if (marketScope === "국내") {
    return "한국";
  }
  if (["AAPL", "NVDA", "GOOGL", "META", "SIRI", "TSM", "C", "NKE"].includes(ticker)) {
    return "미국";
  }
  return "기타해외";
}

function inferThemeCategory(theme: string, assetClass: string, themeCategory: string): string {
  if (themeCategory) {
    return themeCategory;
  }
  if (assetClass === "ETF") {
    return "ETF / 패시브";
  }
  if (["AI", "반도체", "빅테크", "미국 빅테크"].includes(theme)) {
    return "성장 기술";
  }
  if (["금융", "배당", "통신", "유틸리티"].includes(theme)) {
    return "인컴 / 방어";
  }
  if (["지주사", "자산주", "건자재", "상사"].includes(theme)) {
    return "자산 가치";
  }
  if (["자동차", "산업재", "방산", "수출주"].includes(theme)) {
    return "경기 민감";
  }
  if (["소비재", "미디어", "바이오"].includes(theme)) {
    return "개별 성장";
  }
  return "기타";
}

export function normalizePortfolioRecords(records: RawRecord[]): PortfolioPosition[] {
  return records
    .map((record, index) => {
      const ticker = toCellString(readField(record, FIELD_ALIASES.ticker));
      const name = toCellString(readField(record, FIELD_ALIASES.name));
      const assetClass = inferAssetClass(name, toCellString(readField(record, FIELD_ALIASES.assetClass)));
      const marketScope = inferMarketScope(ticker, assetClass, toCellString(readField(record, FIELD_ALIASES.marketScope)));
      const country = inferCountry(marketScope, ticker, toCellString(readField(record, FIELD_ALIASES.country)));
      const theme = toCellString(readField(record, FIELD_ALIASES.theme)) || "미분류";

      return {
        rowId: `${ticker || "row"}-${name || "position"}-${index + 1}`,
        ticker,
        name,
        marketScope,
        assetClass,
        country,
        theme,
        themeCategory: inferThemeCategory(
          theme,
          assetClass,
          toCellString(readField(record, FIELD_ALIASES.themeCategory)),
        ),
        subTheme: toCellString(readField(record, FIELD_ALIASES.subTheme)),
        strategy: toCellString(readField(record, FIELD_ALIASES.strategy)),
        styleBucket: toCellString(readField(record, FIELD_ALIASES.styleBucket)),
        trendView: toCellString(readField(record, FIELD_ALIASES.trendView)) || "미분류",
        cycleView: toCellString(readField(record, FIELD_ALIASES.cycleView)),
        conviction: toCellString(readField(record, FIELD_ALIASES.conviction)),
        fxExposure: toCellString(readField(record, FIELD_ALIASES.fxExposure)),
        timingView: toCellString(readField(record, FIELD_ALIASES.timingView)),
        actualWeightPct: parseNumber(readField(record, FIELD_ALIASES.actualWeightPct)),
        targetWeightPct: parseNumber(readField(record, FIELD_ALIASES.targetWeightPct)),
        per: parseNullableNumber(readField(record, FIELD_ALIASES.per)),
        pbr: parseNullableNumber(readField(record, FIELD_ALIASES.pbr)),
        eps: parseNullableNumber(readField(record, FIELD_ALIASES.eps)),
        forwardPer: parseNullableNumber(readField(record, FIELD_ALIASES.forwardPer)),
        plannedAction: toCellString(readField(record, FIELD_ALIASES.plannedAction)) || "미분류",
        notes: toCellString(readField(record, FIELD_ALIASES.notes)),
      };
    })
    .filter((row) => row.ticker && row.name)
    .sort((left, right) => right.actualWeightPct - left.actualWeightPct);
}

function buildMix(rows: PortfolioPosition[], key: keyof PortfolioPosition) {
  const stats = new Map<string, { label: string; actualWeightPct: number; targetWeightPct: number }>();

  for (const row of rows) {
    const label = String(row[key] || "미분류");
    const current = stats.get(label) ?? { label, actualWeightPct: 0, targetWeightPct: 0 };
    current.actualWeightPct += row.actualWeightPct;
    current.targetWeightPct += row.targetWeightPct;
    stats.set(label, current);
  }

  return [...stats.values()].sort((left, right) => right.actualWeightPct - left.actualWeightPct);
}

export function buildPortfolioSnapshot(rows: PortfolioPosition[]) {
  const actualWeightSum = rows.reduce((sum, row) => sum + row.actualWeightPct, 0);
  const targetWeightSum = rows.reduce((sum, row) => sum + row.targetWeightPct, 0);
  const themeMix = buildMix(rows, "theme");
  const regionMix = buildMix(rows, "marketScope");
  const assetMix = buildMix(rows, "assetClass");
  const trendMix = buildMix(rows, "trendView");
  const actionMix = buildMix(rows, "plannedAction");
  const themeCategoryMix = buildMix(rows, "themeCategory");
  const sortedByActual = [...rows].sort((left, right) => right.actualWeightPct - left.actualWeightPct);
  const sortedByGap = [...rows].sort(
    (left, right) =>
      right.targetWeightPct -
      right.actualWeightPct -
      (left.targetWeightPct - left.actualWeightPct),
  );
  const sortedByTrim = [...rows].sort(
    (left, right) =>
      left.targetWeightPct -
      left.actualWeightPct -
      (right.targetWeightPct - right.actualWeightPct),
  );
  const buyCandidates = sortedByGap
    .filter((row) => row.targetWeightPct > row.actualWeightPct)
    .slice(0, 5);
  const trimCandidates = sortedByTrim
    .filter((row) => row.actualWeightPct > row.targetWeightPct)
    .slice(0, 5);
  const domesticWeight =
    rows.filter((row) => row.marketScope === "국내").reduce((sum, row) => sum + row.actualWeightPct, 0);
  const overseasWeight =
    rows.filter((row) => row.marketScope === "해외").reduce((sum, row) => sum + row.actualWeightPct, 0);
  const topFiveWeight = sortedByActual.slice(0, 5).reduce((sum, row) => sum + row.actualWeightPct, 0);
  const cashDrag = targetWeightSum - actualWeightSum;

  return {
    actualWeightSum,
    targetWeightSum,
    cashDrag,
    themeMix,
    themeCategoryMix,
    regionMix,
    assetMix,
    trendMix,
    actionMix,
    domesticWeight,
    overseasWeight,
    topFiveWeight,
    buyCandidates,
    trimCandidates,
    holdingCount: rows.length,
    themeCount: new Set(rows.map((row) => row.theme)).size,
    countries: new Set(rows.map((row) => row.country)).size,
    coreHoldings: [...rows].sort((left, right) => right.targetWeightPct - left.targetWeightPct).slice(0, 8),
  };
}
