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

# Load environment variables from the project root
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(ROOT_DIR, '.env')
load_dotenv(env_path, override=True)

# Parse command‑line arguments
parser = argparse.ArgumentParser(description="Run scheduling optimizer")
parser.add_argument("--local", action="store_true", help="Force local mode using JSON files")
args = parser.parse_args()

# In API context, sys.argv might not have --local, but we should also check the ROOT .env
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

def solve_schedule():
    staff_members = fetch_staff()
    if not staff_members:
        print("No active staff found. Aborting.")
        return None

    num_staff = len(staff_members)
    num_days = 7  # One‑week schedule
    shifts = ["Morning", "Night"]  # Two shifts per day
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
        max_shifts = person.get("max_shifts_per_week", 5)
        model.Add(
            sum(shift_vars[(s, d, i)] for d in range(num_days) for i in range(num_shifts))
            <= max_shifts
        )

    # Constraint 4: At least one Manager per day
    manager_indices = [s for s, person in enumerate(staff_members) if person.get("role") == "Manager"]
    if manager_indices:
        for d in range(num_days):
            model.Add(sum(shift_vars[(s, d, i)] for s in manager_indices for i in range(num_shifts)) >= 1)

    start_date = datetime.date.today()
    
    # Constraint 5: Time Off Requests (Hard Constraint)
    for s, person in enumerate(staff_members):
        time_off_dates = person.get("time_off", [])
        if time_off_dates:
            for d in range(num_days):
                current_date_str = (start_date + datetime.timedelta(days=d)).isoformat()
                if current_date_str in time_off_dates:
                    for i in range(num_shifts):
                        model.Add(shift_vars[(s, d, i)] == 0)

    # Soft Constraints: Preferences (Objective Function)
    objective_terms = []
    for s, person in enumerate(staff_members):
        preferences = person.get("preferences", {})
        for d in range(num_days):
            current_date_str = (start_date + datetime.timedelta(days=d)).isoformat()
            if current_date_str in preferences:
                weight = preferences[current_date_str]
                for i in range(num_shifts):
                    objective_terms.append(weight * shift_vars[(s, d, i)])
                    
    if objective_terms:
        model.Maximize(sum(objective_terms))

    print("Matrix built. Solving constraints...")
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("Optimal/Feasible schedule found! Preparing output...")
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
            f"Successfully generated a 7‑day schedule for {num_staff} staff members, "
            f"filling {num_days * num_shifts} total shifts while respecting maximum shift limits."
        )
        if not LOCAL_MODE:
            supabase.table("solver_logs").insert({"log_text": log_text}).execute()
        return shift_records
    else:
        print("Failed: No feasible schedule found with given constraints.")
        return None

def solve_and_upload():
    solve_schedule()

if __name__ == "__main__":
    solve_and_upload()