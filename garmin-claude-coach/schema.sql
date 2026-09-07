-- Garmin -> Claude : Supabase schema
-- Tables the daily pull (garmin_daily_pull.py) upserts into. Column names match
-- exactly what the script writes. Run this once in your Supabase SQL editor.
-- Keep RLS ON: the pull writes with the service_role key; a dashboard reads via a
-- server-side proxy (never ship the service key to the browser).

create table if not exists garmin_activities (
  activity_id      bigint primary key,
  activity_date    date,
  started_at       timestamptz,
  activity_type    text,
  name             text,
  duration_s       int,
  distance_m       int,
  avg_hr           int,
  max_hr           int,
  calories         int,
  elevation_gain_m int,
  aerobic_te       numeric,
  anaerobic_te     numeric,
  training_load    numeric,
  moderate_min     int,
  vigorous_min     int,
  created_at       timestamptz default now()
);

create table if not exists garmin_sleep (
  sleep_date      date primary key,
  started_at      timestamptz,
  ended_at        timestamptz,
  total_sleep_s   int,
  deep_s          int,
  light_s         int,
  rem_s           int,
  awake_s         int,
  sleep_score     int,
  avg_respiration numeric,
  avg_stress      int,
  created_at      timestamptz default now()
);

create table if not exists garmin_daily_summary (
  summary_date    date primary key,
  total_steps     int,
  step_goal       int,
  distance_m      int,
  total_calories  int,
  active_calories int,
  resting_hr      int,
  min_hr          int,
  max_hr          int,
  moderate_min    int,
  vigorous_min    int,
  floors_ascended int,
  created_at      timestamptz default now()
);

-- THE EDGE: body-composition off the Index scale (weight / muscle / body fat)
create table if not exists garmin_weigh_ins (
  measured_at    timestamptz primary key,
  measured_date  date,
  weight_kg      numeric,
  bmi            numeric,
  body_fat_pct   numeric,
  body_water_pct numeric,
  muscle_mass_kg numeric,
  bone_mass_kg   numeric,
  source         text,
  created_at     timestamptz default now()
);

create table if not exists garmin_hrv (
  date       date primary key,
  hrv_avg    int,
  hrv_status text,
  created_at timestamptz default now()
);

create table if not exists garmin_race_predictions (
  date        date primary key,
  time_5k_s   int,
  time_10k_s  int,
  time_half_s int,
  time_full_s int,
  created_at  timestamptz default now()
);

alter table garmin_activities        enable row level security;
alter table garmin_sleep             enable row level security;
alter table garmin_daily_summary     enable row level security;
alter table garmin_weigh_ins         enable row level security;
alter table garmin_hrv               enable row level security;
alter table garmin_race_predictions  enable row level security;
