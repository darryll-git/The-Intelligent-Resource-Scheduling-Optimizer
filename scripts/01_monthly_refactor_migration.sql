-- 1. Truncate old data to ensure pristine state
TRUNCATE TABLE public.fact_shifts;

-- 2. Add monthly shift limits and historical tracking to dim_staff
ALTER TABLE public.dim_staff 
ADD COLUMN IF NOT EXISTS max_shifts_per_month integer NOT NULL DEFAULT 20,
ADD COLUMN IF NOT EXISTS historical_shift_counts jsonb DEFAULT '{"morning": 0, "afternoon": 0, "evening": 0, "night": 0}'::jsonb;

-- 3. Create a table for employee timing preferences
CREATE TABLE IF NOT EXISTS public.staff_preferences (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  staff_id text NOT NULL,
  preferred_shift_type text NOT NULL CHECK (preferred_shift_type IN ('morning', 'afternoon', 'evening', 'night')),
  preference_weight integer NOT NULL DEFAULT 1, -- 1: Nice to have, 5: Strong preference
  day_of_week integer CHECK (day_of_week BETWEEN 0 AND 6), -- Optional: 0=Sunday, null=Every day
  created_at timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
  CONSTRAINT staff_preferences_pkey PRIMARY KEY (id),
  CONSTRAINT staff_preferences_staff_id_fkey FOREIGN KEY (staff_id) REFERENCES public.dim_staff(staff_id) ON DELETE CASCADE
);

-- 4. Enforce strict shift types on fact_shifts
ALTER TABLE public.fact_shifts
DROP CONSTRAINT IF EXISTS fact_shifts_shift_type_check;

ALTER TABLE public.fact_shifts
ADD CONSTRAINT fact_shifts_shift_type_check 
CHECK (shift_type IN ('morning', 'afternoon', 'evening', 'night'));
