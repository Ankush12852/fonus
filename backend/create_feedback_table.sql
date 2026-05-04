CREATE TABLE public.feedback (
  id uuid default gen_random_uuid() primary key,
  user_id uuid null references auth.users(id),
  module text not null,
  type text not null,
  message text not null,
  status text default 'unread',
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);
