-- UMD Nutrition scraper schema
create extension if not exists pg_trgm;

create table if not exists dining_halls (
  id    smallint primary key,
  name  text not null,
  slug  text unique not null
);

insert into dining_halls (id, name, slug) values
  (16, 'South Campus', 'south-campus'),
  (19, 'Yahentamitsi Dining Hall', 'yahentamitsi'),
  (51, '251 North', '251-north')
on conflict (id) do update set name = excluded.name, slug = excluded.slug;

create table if not exists foods (
  id               bigserial primary key,
  rec_num          integer not null,
  portion          smallint not null,
  name             text not null,
  serving_size     text,
  servings_per     text,
  calories         numeric,
  total_fat_g      numeric,
  sat_fat_g        numeric,
  trans_fat_g      numeric,
  cholesterol_mg   numeric,
  sodium_mg        numeric,
  total_carbs_g    numeric,
  fiber_g          numeric,
  sugars_g         numeric,
  added_sugars_g   numeric,
  protein_g        numeric,
  iron_mg          numeric,
  calcium_mg       numeric,
  potassium_mg     numeric,
  vitamin_a_mcg    numeric,
  vitamin_c_mg     numeric,
  ingredients      text,
  label_scraped_at timestamptz,
  label_missing    boolean not null default false,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  unique (rec_num, portion)
);

create index if not exists foods_name_trgm on foods using gin (name gin_trgm_ops);
create index if not exists foods_fts on foods using gin (to_tsvector('english', name || ' ' || coalesce(ingredients, '')));
create index if not exists foods_rec_num on foods (rec_num);
create index if not exists foods_calories on foods (calories);
create index if not exists foods_protein on foods (protein_g);
create index if not exists foods_carbs on foods (total_carbs_g);
create index if not exists foods_sodium on foods (sodium_mg);

create table if not exists food_allergens (
  food_id  bigint not null references foods(id) on delete cascade,
  allergen text not null check (allergen in ('dairy','eggs','fish','gluten','nuts','sesame','shellfish','soy')),
  primary key (food_id, allergen)
);
create index if not exists food_allergens_allergen on food_allergens (allergen);

create table if not exists food_dietary_tags (
  food_id bigint not null references foods(id) on delete cascade,
  tag     text not null check (tag in ('vegan','vegetarian','halal','local','smart_choice')),
  primary key (food_id, tag)
);
create index if not exists food_dietary_tags_tag on food_dietary_tags (tag);

create table if not exists menu_offerings (
  id          bigserial primary key,
  food_id     bigint not null references foods(id) on delete cascade,
  hall_id     smallint not null references dining_halls(id),
  served_date date not null,
  meal        text not null check (meal in ('breakfast','lunch','brunch','dinner')),
  station     text,
  scraped_at  timestamptz not null default now(),
  unique (food_id, hall_id, served_date, meal)
);
create index if not exists menu_offerings_lookup on menu_offerings (hall_id, served_date, meal);
create index if not exists menu_offerings_daily on menu_offerings (served_date, meal);
create index if not exists menu_offerings_food_date on menu_offerings (food_id, served_date desc);

create table if not exists scrape_runs (
  id            bigserial primary key,
  started_at    timestamptz not null default now(),
  finished_at   timestamptz,
  hall_id       smallint references dining_halls(id),
  served_date   date,
  meal          text,
  status        text not null check (status in ('ok','closed','empty','error')),
  items_found   integer,
  error_message text
);
create index if not exists scrape_runs_recent on scrape_runs (started_at desc);

create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

drop trigger if exists foods_updated_at on foods;
create trigger foods_updated_at before update on foods
for each row execute function set_updated_at();
