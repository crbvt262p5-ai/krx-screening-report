export const PORTFOLIO_SESSION_COOKIE = "portfolio_session";
export const PORTFOLIO_SESSION_MAX_AGE = 60 * 60 * 24 * 30;

function getAuthConfig() {
  const password = process.env.PORTFOLIO_ACCESS_PASSWORD;
  const secret = process.env.PORTFOLIO_SESSION_SECRET;

  if (!password || !secret) {
    return null;
  }

  return { password, secret };
}

async function signSession(password: string, secret: string) {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(`${secret}:${password}`),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", key, encoder.encode("portfolio-session-v1"));

  return Array.from(new Uint8Array(signature), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export function isPortfolioAuthConfigured() {
  return getAuthConfig() !== null;
}

export async function createPortfolioSessionToken() {
  const config = getAuthConfig();
  if (!config) {
    return null;
  }

  return signSession(config.password, config.secret);
}

export async function verifyPortfolioPassword(candidate: string) {
  const config = getAuthConfig();
  if (!config || candidate.length !== config.password.length) {
    return false;
  }

  let mismatch = 0;
  for (let index = 0; index < candidate.length; index += 1) {
    mismatch |= candidate.charCodeAt(index) ^ config.password.charCodeAt(index);
  }

  return mismatch === 0;
}

export async function verifyPortfolioSession(token: string | undefined) {
  if (!token) {
    return false;
  }

  const expected = await createPortfolioSessionToken();
  if (!expected || token.length !== expected.length) {
    return false;
  }

  let mismatch = 0;
  for (let index = 0; index < token.length; index += 1) {
    mismatch |= token.charCodeAt(index) ^ expected.charCodeAt(index);
  }

  return mismatch === 0;
}
