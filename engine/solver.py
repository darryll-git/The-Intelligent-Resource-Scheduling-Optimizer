import os
import json
import argparse
import datetime
from dotenv import load_dotenv
from ortools.sat.python import cp_model

# Optional Supabase import; only used if credentials are provided
try:
    from supabase import create_client, Client
except Exception:
    Client = None
    def create_client(url, key):
        raise ImportError("Supabase client not available")

# Load environment variables
load_dotenv()

# Parse command‑line arguments
parser = argparse.ArgumentParser(description="Run scheduling optimizer")
parser.add_argument("--local", action="store_true", help="Force local mode using JSON files")
args = parser.parse_args()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
LOCAL_MODE = args.local or not (SUPABASE_URL and SUPABASE_KEY)

if not LOCAL_MODE:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None
    print("Running in LOCAL mode – using JSON files for data storage.")

# Paths for local JSON storage
BASE_DIR = os.path.dirname(__file__)
STAFF_DATA_PATH = os.path.join(BASE_DIR, "staff_data.json")
SCHEDULE_OUTPUT_PATH = os.path.join(BASE_DIR, "schedule_output.json")

def fetch_staff():
    """Fetch staff constraints from Supabase or a local JSON file.

    Returns:
        list[dict]: List of staff records.
    """
    if LOCAL_MODE:
        if not os.path.exists(STAFF_DATA_PATH):
            print(f"Staff data file not found at {STAFF_DATA_PATH}")
            return []
        with open(STAFF_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"Loaded {len(data)} staff records from local JSON.")
        return data
    else:
        print("Fetching staff constraints from Supabase...")
        response = supabase.table("dim_staff").select("*").eq("is_active", True).execute()
        return response.data

def upload_schedule_local(shift_records):
    """Write schedule to a JSON file in local mode."""
    try:
        # Save to engine directory
        with open(SCHEDULE_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(shift_records, f, indent=2, default=str)
        print(f"Schedule written to {SCHEDULE_OUTPUT_PATH} ({len(shift_records)} records).")
        
        # Also save to frontend/public for the React app if it exists
        frontend_public_path = os.path.join(os.path.dirname(BASE_DIR), "frontend", "public", "schedule.json")
        if os.path.exists(os.path.dirname(frontend_public_path)):
            with open(frontend_public_path, "w", encoding="utf-8") as f:
                json.dump(shift_records, f, indent=2, default=str)
            print(f"Schedule also synchronized to {frontend_public_path}")
            
    except Exception as e:
        print(f"Failed to write schedule locally: {e}")

def solve_and_upload(payload=None):
    if payload is None:
        payload = {}
        
    staff_members = fetch_staff()
    if not staff_members:
        print("No active staff found. Aborting.")
        return

    num_staff = len(staff_members)
    
    # Dynamic inputs from JSON payload
    num_days = payload.get("num_days", 7)
    shifts = payload.get("shifts", ["Morning", "Night"])
    num_shifts = len(shifts)

    # Build OR‑Tools model
    model = cp_model.CpModel()
    shift_vars = {}
    for s in range(num_staff):
        for d in range(num_days):
            for i in range(num_shifts):
                shift_vars[(s, d, i)] = model.NewBoolVar(f"shift_s{s}_d{d}_i{i}")

    # Constraint 1: Exactly one staff per shift
    for d in range(num_days):
        for i in range(num_shifts):
            model.AddExactlyOne(shift_vars[(s, d, i)] for s in range(num_staff))

    # Constraint 2: At most one shift per staff per day
    for s in range(num_staff):
        for d in range(num_days):
            model.AddAtMostOne(shift_vars[(s, d, i)] for i in range(num_shifts))

    # Constraint 3: Respect max_shifts_per_week from data
    for s, person in enumerate(staff_members):
        max_shifts_per_week = person.get("max_shifts_per_week", 5)
        # Scale the max limit depending on the dynamic time horizon
        max_shifts = int(max_shifts_per_week * (num_days / 7.0))
        model.Add(
            sum(shift_vars[(s, d, i)] for d in range(num_days) for i in range(num_shifts))
            <= max_shifts
        )
        
    # Phase 2: Soft Constraints & Objective Function
    penalty_vars = []
    
    # Soft Constraint A: Penalize back-to-back shifts (Night followed by Morning next day)
    night_idx = shifts.index("Night") if "Night" in shifts else -1
    morning_idx = shifts.index("Morning") if "Morning" in shifts else -1
    
    if night_idx != -1 and morning_idx != -1:
        for s in range(num_staff):
            for d in range(num_days - 1):
                b2b_penalty = model.NewBoolVar(f"b2b_s{s}_d{d}")
                # b2b_penalty must be True if s works Night on day d and Morning on day d+1
                model.Add(b2b_penalty >= shift_vars[(s, d, night_idx)] + shift_vars[(s, d+1, morning_idx)] - 1)
                # Assign a heavy penalty weight
                penalty_vars.append(b2b_penalty * 100)
                
    # Soft Constraint B: Penalize uneven shift distributions (Maximize fairness)
    max_shifts_var = model.NewIntVar(0, num_days * num_shifts, "max_shifts")
    min_shifts_var = model.NewIntVar(0, num_days * num_shifts, "min_shifts")
    
    for s in range(num_staff):
        total_shifts_s = sum(shift_vars[(s, d, i)] for d in range(num_days) for i in range(num_shifts))
        model.Add(total_shifts_s <= max_shifts_var)
        model.Add(total_shifts_s >= min_shifts_var)
        
    # The fairness penalty is the difference between the most and least shifts assigned to any staff
    fairness_diff = model.NewIntVar(0, num_days * num_shifts, "fairness_diff")
    model.Add(fairness_diff == max_shifts_var - min_shifts_var)
    penalty_vars.append(fairness_diff * 50)
    
    # Set the objective function to minimize total penalties
    model.Minimize(sum(penalty_vars))

    print("Matrix built. Solving constraints...")
    solver = cp_model.CpSolver()
    # Add a max time limit to prevent infinite searching
    solver.parameters.max_time_in_seconds = 10.0
    status = solver.Solve(model)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print(f"Optimal schedule found! Status: {solver.StatusName(status)}")
        start_date = datetime.date.today()
        shift_records = []
        for d in range(num_days):
            current_date = start_date + datetime.timedelta(days=d)
            for i, shift_name in enumerate(shifts):
                for s in range(num_staff):
                    if solver.Value(shift_vars[(s, d, i)]):
                        shift_records.append({
                            "staff_id": staff_members[s]["staff_id"],
                            "shift_date": current_date.isoformat(),
                            "shift_type": shift_name,
                            "is_locked": False,
                        })
        if LOCAL_MODE:
            upload_schedule_local(shift_records)
        else:
            supabase.table("fact_shifts").insert(shift_records).execute()
            print(f"Success! Pushed {len(shift_records)} shifts to 'fact_shifts'.")
        # Log reasoning (simple text)
        log_text = (
            f"Successfully generated a {num_days}‑day schedule for {num_staff} staff members, "
            f"filling {num_days * num_shifts} total shifts while optimizing fairness and back-to-back constraints."
        )
        if not LOCAL_MODE:
            supabase.table("solver_logs").insert({"log_text": log_text}).execute()
    else:
        print("Failed: No feasible schedule found with given constraints.")

if __name__ == "__main__":
    solve_and_upload()