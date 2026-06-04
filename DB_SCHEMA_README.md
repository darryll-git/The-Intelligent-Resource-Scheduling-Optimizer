# Database Schema & AI Embeddings 🧠💾

This document outlines the new PostgreSQL database functionality introduced to **The Intelligent Resource & Scheduling Optimizer**. 

By migrating from local JSON files (`staff_data.json` & `schedule_output.json`) to a relational database (like Supabase), the system now supports scalable data persistence, analytics, and AI-powered retrieval-augmented generation (RAG) through vector embeddings.

---

## 🗄️ Schema Overview

The database follows a star-schema inspired design, optimized for both transactional scheduling and analytical querying.

### 1. `dim_staff`
The dimension table storing the workforce profile and their scheduling constraints.

**Schema:**
```sql
CREATE TABLE public.dim_staff (
  staff_id integer NOT NULL DEFAULT nextval('dim_staff_staff_id_seq'::regclass),
  full_name text NOT NULL,
  role text NOT NULL,
  max_shifts_per_week integer DEFAULT 5,
  is_active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()),
  CONSTRAINT dim_staff_pkey PRIMARY KEY (staff_id)
);
```

**Sample Data:**
| staff_id | full_name | role | max_shifts_per_week | is_active |
|---|---|---|---|---|
| 1 | Dr. Sarah Connor | Lead Physician | 4 | true |
| 2 | John Smith | Nurse | 5 | true |
| 3 | Alice Johnson | Technician | 5 | true |

---

### 2. `fact_shifts`
The central fact table representing the generated shift assignments output by the Google OR-Tools optimization engine.

**Schema:**
```sql
CREATE TABLE public.fact_shifts (
  shift_id integer NOT NULL DEFAULT nextval('fact_shifts_shift_id_seq'::regclass),
  staff_id integer,
  shift_date date NOT NULL,
  shift_type text NOT NULL,
  is_locked boolean DEFAULT false,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()),
  CONSTRAINT fact_shifts_pkey PRIMARY KEY (shift_id),
  CONSTRAINT fact_shifts_staff_id_fkey FOREIGN KEY (staff_id) REFERENCES public.dim_staff(staff_id)
);
```

**Sample Data:**
| shift_id | staff_id | shift_date | shift_type | is_locked |
|---|---|---|---|---|
| 1 | 3 (Alice Johnson) | 2026-04-07 | Morning | false |
| 2 | 2 (John Smith) | 2026-04-07 | Night | false |
| 3 | 2 (John Smith) | 2026-04-08 | Morning | false |

*Note: The optimizer successfully enforces constraints (e.g., max shifts per week) and avoids double shifts on the same day.*

---

### 3. `solver_logs` (AI Vector Embeddings)
This table acts as an audit trail for the OR-Tools engine and powers the system's Natural Language AI Interface. 

When the solver creates a schedule, it logs the constraints it processed and the results it achieved. The `embedding` column stores vector representations of these logs, enabling semantic search and RAG capabilities (e.g., querying the schedule with "Why wasn't Dr. Connor scheduled on the 10th?").

**Schema:**
```sql
CREATE TABLE public.solver_logs (
  log_id integer NOT NULL DEFAULT nextval('solver_logs_log_id_seq'::regclass),
  log_text text NOT NULL,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()),
  embedding USER-DEFINED, -- pgvector extension for LLM embeddings
  CONSTRAINT solver_logs_pkey PRIMARY KEY (log_id)
);
```

**Sample Log Entry:**
> *"Successfully generated a 7-day schedule for 3 staff members, filling 14 total shifts while strictly adhering to weekly maximum shift constraints. No double shifts were assigned."*

## 🚀 Moving to Production (Supabase)

To utilize this new functionality:
1. Ensure your PostgreSQL database has the `pgvector` extension enabled for the `embedding` column.
2. Update your `.env` file with `SUPABASE_URL` and `SUPABASE_KEY`.
3. Run the engine without the `--local` flag to write directly to these tables.
