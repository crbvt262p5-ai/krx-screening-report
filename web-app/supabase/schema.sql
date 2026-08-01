create extension if not exists "pgcrypto";

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.dogs (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  weight_kg numeric(5,2) not null check (weight_kg > 0),
  age_group text not null check (age_group in ('puppy', 'adult', 'senior')),
  activity_factor numeric(4,2) not null check (activity_factor > 0),
  is_neutered boolean not null default true,
  note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.products (
  id uuid primary key default gen_random_uuid(),
  source_type text not null check (source_type in ('manual', 'internal', 'open_pet_food_facts')),
  external_id text,
  kind text not null check (kind in ('food', 'treat')),
  name text not null,
  brand text not null default '',
  total_weight_g numeric(8,2),
  kcal_per_100g numeric(8,2),
  total_kcal numeric(8,2),
  pieces_per_pack integer,
  kcal_per_piece numeric(8,2),
  image_url text,
  verified boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.product_aliases (
  id uuid primary key default gen_random_uuid(),
  product_id uuid not null references public.products(id) on delete cascade,
  alias text not null,
  locale text not null default 'ko',
  created_at timestamptz not null default now()
);

create table if not exists public.feeding_logs (
  id uuid primary key default gen_random_uuid(),
  dog_id uuid not null references public.dogs(id) on delete cascade,
  log_date date not null,
  food_product_id uuid references public.products(id) on delete set null,
  treat_product_id uuid references public.products(id) on delete set null,
  food_grams numeric(8,2) not null default 0,
  treat_pieces integer not null default 0,
  food_kcal numeric(8,2) not null default 0,
  treat_kcal numeric(8,2) not null default 0,
  total_kcal numeric(8,2) not null default 0,
  recommended_kcal numeric(8,2) not null default 0,
  note text,
  created_at timestamptz not null default now()
);

create table if not exists public.portfolio_positions (
  row_id text primary key,
  ticker text not null,
  name text not null,
  market_scope text not null,
  asset_class text not null,
  country text not null,
  theme text not null,
  sub_theme text,
  strategy text,
  style_bucket text,
  trend_view text,
  cycle_view text,
  conviction text,
  fx_exposure text,
  timing_view text,
  actual_weight_pct numeric(8,2) not null default 0,
  target_weight_pct numeric(8,2) not null default 0,
  planned_action text,
  notes text,
  sort_order integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists dogs_created_at_idx on public.dogs (created_at desc);
create index if not exists products_kind_idx on public.products (kind);
create index if not exists products_name_idx on public.products (name);
create index if not exists product_aliases_product_id_idx on public.product_aliases (product_id);
create index if not exists product_aliases_alias_idx on public.product_aliases (alias);
create index if not exists feeding_logs_dog_id_log_date_idx on public.feeding_logs (dog_id, log_date desc);
create index if not exists portfolio_positions_sort_order_idx on public.portfolio_positions (sort_order asc);

drop trigger if exists dogs_set_updated_at on public.dogs;
create trigger dogs_set_updated_at
before update on public.dogs
for each row execute function public.set_updated_at();

drop trigger if exists products_set_updated_at on public.products;
create trigger products_set_updated_at
before update on public.products
for each row execute function public.set_updated_at();

drop trigger if exists portfolio_positions_set_updated_at on public.portfolio_positions;
create trigger portfolio_positions_set_updated_at
before update on public.portfolio_positions
for each row execute function public.set_updated_at();

alter table public.dogs enable row level security;
alter table public.products enable row level security;
alter table public.product_aliases enable row level security;
alter table public.feeding_logs enable row level security;
alter table public.portfolio_positions enable row level security;

drop policy if exists "public read dogs" on public.dogs;
create policy "public read dogs" on public.dogs for select using (true);

drop policy if exists "public write dogs" on public.dogs;
create policy "public write dogs" on public.dogs for insert with check (true);

drop policy if exists "public update dogs" on public.dogs;
create policy "public update dogs" on public.dogs for update using (true) with check (true);

drop policy if exists "public read products" on public.products;
create policy "public read products" on public.products for select using (true);

drop policy if exists "public write products" on public.products;
create policy "public write products" on public.products for insert with check (true);

drop policy if exists "public update products" on public.products;
create policy "public update products" on public.products for update using (true) with check (true);

drop policy if exists "public read aliases" on public.product_aliases;
create policy "public read aliases" on public.product_aliases for select using (true);

drop policy if exists "public write aliases" on public.product_aliases;
create policy "public write aliases" on public.product_aliases for insert with check (true);

drop policy if exists "public read feeding logs" on public.feeding_logs;
create policy "public read feeding logs" on public.feeding_logs for select using (true);

drop policy if exists "public write feeding logs" on public.feeding_logs;
create policy "public write feeding logs" on public.feeding_logs for insert with check (true);

drop policy if exists "public read portfolio positions" on public.portfolio_positions;
drop policy if exists "public write portfolio positions" on public.portfolio_positions;
drop policy if exists "public update portfolio positions" on public.portfolio_positions;
drop policy if exists "public delete portfolio positions" on public.portfolio_positions;

-- Portfolio data is private. The application accesses it only with the server-side
-- service role after its own password gate has authenticated the request.
