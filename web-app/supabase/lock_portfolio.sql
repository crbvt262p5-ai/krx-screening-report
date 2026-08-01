alter table public.portfolio_positions enable row level security;

drop policy if exists "public read portfolio positions" on public.portfolio_positions;
drop policy if exists "public write portfolio positions" on public.portfolio_positions;
drop policy if exists "public update portfolio positions" on public.portfolio_positions;
drop policy if exists "public delete portfolio positions" on public.portfolio_positions;

revoke all on table public.portfolio_positions from anon;
revoke all on table public.portfolio_positions from authenticated;
