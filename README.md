# The Intelligent Resource & Scheduling Optimizer ⚙️🧠

An end‑to‑end, AI‑enhanced scheduling and logistics optimizer designed to run **locally** on low‑budget hardware.

## 📖 Project Overview

The optimizer ingests raw scheduling constraints, computes optimal resource allocations using Google OR‑Tools, and provides a natural‑language querying interface via an LLM (optional). The architecture now runs **entirely locally** – no external n8n orchestrator required.

## 🏗️ Architecture (Local Mode)

1. **Engine (Local OR‑Tools)** – Core scheduling algorithm (`engine/solver.py`).
2. **Data Store** – By default uses local JSON files (`staff_data.json` & `schedule_output.json`). Optionally you can enable Supabase by setting `SUPABASE_URL` and `SUPABASE_KEY` in the `.env` file.
3. **Frontend (React)** – Lightweight UI in `frontend/` (optional, can be started with `npm install && npm start`).

## 🚀 Getting Started (Local Execution)

1. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```
2. **Create a virtual environment (optional but recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate   # on Windows: venv\Scripts\activate
   ```
3. **Prepare data** – Edit `engine/staff_data.json` to include your staff records. Sample data is provided.
4. **Run the optimizer**
   ```bash
   python engine/solver.py --local
   ```
   The schedule will be written to `engine/schedule_output.json`.
5. **Optional Supabase mode** – Fill `SUPABASE_URL` and `SUPABASE_KEY` in `.env` and omit `--local` flag.

## 📂 Project Structure
```
Intelligent‑Scheduler/
├── engine/                  # Local OR‑Tools optimization logic
│   ├── solver.py            # Core scheduling algorithm (supports local & Supabase modes)
│   ├── staff_data.json      # Sample staff constraints (local mode)
│   ├── schedule_output.json # Generated schedule (local mode)
│   └── requirements.txt     # Python dependencies
├── frontend/                # React UI (optional)
│   └── ...
├── .env                     # Environment variables (place Supabase credentials here if needed)
├── README.md                # This file
```

## 🛠️ Clean‑up
The original `n8n_workflows` directory has been removed as it is no longer required for local execution.

---