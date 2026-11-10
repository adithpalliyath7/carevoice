-- CareVoice — Supabase (PostgreSQL) schema. Run in the Supabase SQL editor.
-- MVP stores data in-memory by default; these tables are the persistence
-- target when SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY are configured.
-- All demo data is fictional. Enable RLS and add auth policies before any
-- real patient data is stored.
create table if not exists hospitals (
  id text primary key, name text not null, location text, phone text,
  emergency_phone text, is_demo boolean default true
);
create table if not exists doctors (
  id text primary key, hospital_id text references hospitals(id),
  name text not null, speciality text not null, qualification text,
  experience_years int, languages text[] default '{}',
  fee_inr int, rating numeric(2,1), location text
);
create table if not exists patients (
  id uuid primary key default gen_random_uuid(),
  name text not null, phone text not null, age int, language text default 'en'
);
create table if not exists slots (
  id uuid primary key default gen_random_uuid(),
  doctor_id text references doctors(id), date date not null, time time not null,
  available boolean default true, source text default 'demo_schedule',
  unique (doctor_id, date, time)
);
create table if not exists appointments (
  token text primary key, doctor_id text references doctors(id),
  patient_id uuid references patients(id), patient_name text, patient_phone text,
  date date not null, time time not null, status text default 'confirmed',
  source text default 'online', for_family_member text, fee_inr int,
  qr_payload text, doctor_notes text, created_at timestamptz default now()
);
create index if not exists idx_appointments_date on appointments(date);
create index if not exists idx_appointments_phone on appointments(patient_phone);

create table if not exists medical_records (
  id text primary key, patient_name text, patient_phone text,
  doctor_name text, kind text, date date, notes text,
  filename text, content_type text, size_bytes bigint,
  storage_ref text, extracted_text text, ocr_status text,
  ocr_confidence numeric(3,2), fields jsonb, created_at timestamptz default now()
);
create index if not exists idx_records_date on medical_records(date);
create index if not exists idx_records_doctor on medical_records(doctor_name);

create table if not exists reminders (
  id text primary key, record_id text references medical_records(id),
  appointment_token text references appointments(token),
  type text, due_date date, note text, language text default 'en',
  created_at timestamptz default now()
);
create table if not exists escalations (
  reference_id text primary key, patient_name text, patient_phone text,
  concern text, severity text, appointment_token text, language text default 'en',
  created_at timestamptz default now()
);
-- Hospital ops
create table if not exists availability (
  doctor_id text primary key references doctors(id),
  weekly jsonb default '{}', blocked_dates jsonb default '{}',
  blocked_slots jsonb default '{}', max_per_day int default 32
);
create table if not exists queue_events (
  id uuid primary key default gen_random_uuid(),
  token text references appointments(token), doctor_id text,
  date date, status text, position int, created_at timestamptz default now()
);
create table if not exists cancellations (
  id uuid primary key default gen_random_uuid(),
  token text, doctor_id text, date date, reason text,
  cancelled_by text, created_at timestamptz default now()
);
create table if not exists delays (
  doctor_id text primary key references doctors(id),
  delay_minutes int, message text, language text default 'en',
  created_at timestamptz default now()
);
create table if not exists waitlist (
  id text primary key, doctor_id text references doctors(id),
  date date, preferred_time time, patient_name text, phone text,
  language text default 'en', status text default 'waiting',
  offer jsonb, appointment_token text, created_at timestamptz default now()
);
create table if not exists analytics_events (
  id uuid primary key default gen_random_uuid(),
  event text, language text, created_at timestamptz default now()
);
create table if not exists feedback (
  id text primary key, appointment_token text, rating int check (rating between 1 and 5),
  note text, voice_note text, created_at timestamptz default now()
);
-- Row Level Security: enable it; add policies tied to Supabase Auth before
-- storing real data. The MVP demo runs without auth by design.
alter table appointments enable row level security;
alter table medical_records enable row level security;
alter table feedback enable row level security;
