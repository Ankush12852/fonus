-- Part B: Add topic_stats column to module_progress table
-- Run this in Supabase SQL editor (https://app.supabase.com → SQL Editor)
--
-- This stores per-topic question attempt counts like:
-- { "6.1": 12, "6.4": 28, "6.5": 0, "9.10": 15 }

ALTER TABLE module_progress
ADD COLUMN IF NOT EXISTS topic_stats JSONB DEFAULT '{}';

-- Optional: verify the column was added
-- SELECT column_name, data_type, column_default
-- FROM information_schema.columns
-- WHERE table_name = 'module_progress'
-- ORDER BY ordinal_position;
