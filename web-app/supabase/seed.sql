insert into public.dogs (id, name, weight_kg, age_group, activity_factor, is_neutered, note)
values
  ('11111111-1111-1111-1111-111111111111', '멜로', 9.0, 'adult', 1.6, true, '식탐이 있어서 간식 칼로리 체크가 중요함'),
  ('22222222-2222-2222-2222-222222222222', '코코', 4.2, 'senior', 1.2, true, null)
on conflict (id) do update
set
  name = excluded.name,
  weight_kg = excluded.weight_kg,
  age_group = excluded.age_group,
  activity_factor = excluded.activity_factor,
  is_neutered = excluded.is_neutered,
  note = excluded.note;

insert into public.products (
  id,
  source_type,
  kind,
  name,
  brand,
  total_weight_g,
  kcal_per_100g,
  total_kcal,
  pieces_per_pack,
  kcal_per_piece,
  verified
)
values
  ('33333333-3333-3333-3333-333333333333', 'internal', 'food', '오리젠 스몰브리드', 'ORIJEN', 1500, 390, 5850, null, null, true),
  ('44444444-4444-4444-4444-444444444444', 'manual', 'treat', '덴탈 소프트 츄', '멍데이', 300, null, 960, 24, 40, true),
  ('55555555-5555-5555-5555-555555555555', 'open_pet_food_facts', 'food', '로얄캐닌 미니 어덜트', 'Royal Canin', 800, 374, 2992, null, null, false)
on conflict (id) do update
set
  source_type = excluded.source_type,
  kind = excluded.kind,
  name = excluded.name,
  brand = excluded.brand,
  total_weight_g = excluded.total_weight_g,
  kcal_per_100g = excluded.kcal_per_100g,
  total_kcal = excluded.total_kcal,
  pieces_per_pack = excluded.pieces_per_pack,
  kcal_per_piece = excluded.kcal_per_piece,
  verified = excluded.verified;

insert into public.product_aliases (product_id, alias, locale)
values
  ('33333333-3333-3333-3333-333333333333', '오리젠', 'ko'),
  ('33333333-3333-3333-3333-333333333333', 'orijen small breed', 'en'),
  ('44444444-4444-4444-4444-444444444444', '덴탈츄', 'ko'),
  ('55555555-5555-5555-5555-555555555555', '로얄캐닌', 'ko')
on conflict do nothing;

insert into public.feeding_logs (
  id,
  dog_id,
  log_date,
  food_product_id,
  treat_product_id,
  food_grams,
  treat_pieces,
  food_kcal,
  treat_kcal,
  total_kcal,
  recommended_kcal,
  note
)
values
  ('66666666-6666-6666-6666-666666666666', '11111111-1111-1111-1111-111111111111', current_date - 1, '33333333-3333-3333-3333-333333333333', '44444444-4444-4444-4444-444444444444', 85, 2, 331.5, 80, 411.5, 364, 'ORIJEN · 권장량과 비슷해요'),
  ('77777777-7777-7777-7777-777777777777', '22222222-2222-2222-2222-222222222222', current_date - 1, '55555555-5555-5555-5555-555555555555', null, 55, 1, 205.7, 35, 240.7, 226.4, 'Royal Canin · 14.3 kcal 많아요')
on conflict (id) do update
set
  dog_id = excluded.dog_id,
  log_date = excluded.log_date,
  food_product_id = excluded.food_product_id,
  treat_product_id = excluded.treat_product_id,
  food_grams = excluded.food_grams,
  treat_pieces = excluded.treat_pieces,
  food_kcal = excluded.food_kcal,
  treat_kcal = excluded.treat_kcal,
  total_kcal = excluded.total_kcal,
  recommended_kcal = excluded.recommended_kcal,
  note = excluded.note;
