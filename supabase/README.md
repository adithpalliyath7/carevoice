# Supabase setup

1. Create a project at https://supabase.com (free tier is enough for the MVP).
2. Open the SQL Editor and run `schema.sql`, then `seed.sql`.
3. In the backend, copy `backend/.env.example` to `backend/.env` and set:
   `SUPABASE_URL=https://<project>.supabase.co`
   `SUPABASE_SERVICE_ROLE_KEY=<service role key>` (server only — never in the frontend).
4. The MVP works fully without Supabase (in-memory store, `demo_mode=true`).
   Supabase wiring is a persistence upgrade, not a requirement to run the demo.
5. Storage: the default records store is local disk (`backend/storage/records/`,
   git-ignored). For Supabase Storage, create a private bucket `medical-records`
   and point `app/storage.py` at it; keep the bucket private and serve files
   only through the authenticated download/share endpoints.
6. Before storing real patient data: enable RLS policies, add Supabase Auth,
   and replace the demo staff login (see README — Production auth warning).
