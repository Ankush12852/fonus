-- Fix PGRST204: backend expects a numeric daily question counter on `daily_usage`.
-- Run in Supabase SQL editor if your table is missing this column.

alter table public.daily_usage
  add column if not exists questions_asked integer not null default 0;
