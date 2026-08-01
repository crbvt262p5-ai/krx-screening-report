type PortfolioLoginPageProps = {
  searchParams: Promise<{ error?: string; next?: string }>;
};

export default async function PortfolioLoginPage({ searchParams }: PortfolioLoginPageProps) {
  const params = await searchParams;
  const hasConfigError = params.error === "config";
  const hasPasswordError = params.error === "invalid";
  const nextPath = params.next?.startsWith("/") && !params.next.startsWith("//") ? params.next : "/portfolio";

  return (
    <main className="portfolio-login-shell">
      <section className="portfolio-login-card">
        <div className="portfolio-login-mark" aria-hidden="true">P</div>
        <p className="portfolio-login-eyebrow">PRIVATE PORTFOLIO</p>
        <h1>내 투자자산</h1>
        <p className="portfolio-login-copy">개인 자산정보 보호를 위해 비밀번호가 필요합니다.</p>

        <form action="/api/portfolio/auth/login" method="post" className="portfolio-login-form">
          <input type="hidden" name="next" value={nextPath} />
          <label htmlFor="portfolio-password">접속 비밀번호</label>
          <input
            id="portfolio-password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            autoFocus
            placeholder="비밀번호 입력"
          />
          {hasPasswordError ? <p className="portfolio-login-error">비밀번호가 맞지 않습니다.</p> : null}
          {hasConfigError ? (
            <p className="portfolio-login-error">서버 보안 설정이 완료되지 않아 접속을 차단했습니다.</p>
          ) : null}
          <button type="submit" disabled={hasConfigError}>안전하게 접속하기</button>
        </form>

        <p className="portfolio-login-note">로그인 정보는 브라우저의 보안 쿠키에만 저장됩니다.</p>
      </section>
    </main>
  );
}
