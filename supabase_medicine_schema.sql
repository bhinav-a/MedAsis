-- Run this in the Supabase SQL editor

create table if not exists public.medicines (
    id uuid primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    name text not null,
    mfd text,
    exp_date text,
    dose text,
    batch_no text,
    manufacturer text,
    raw_text text,
    other_info text,
    image_path text,
    added_date timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists medicines_user_id_idx on public.medicines (user_id);
create index if not exists medicines_user_name_idx on public.medicines (user_id, name);

alter table public.medicines enable row level security;

create policy "Users can read their medicines"
on public.medicines
for select
using (auth.uid() = user_id);

create policy "Users can insert their medicines"
on public.medicines
for insert
with check (auth.uid() = user_id);

create policy "Users can update their medicines"
on public.medicines
for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "Users can delete their medicines"
on public.medicines
for delete
using (auth.uid() = user_id);
