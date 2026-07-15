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
        print("Fetching staff constraints and preferences from Supabase...")
        response = supabase.table("dim_staff").select("*, staff_preferences(*)").eq("is_active", True).execute()
        
        # staff_preferences will be mapped to "preferences" list in the solver logic
        data = response.data
        for person in data:
            if "staff_preferences" in person:
                person["preferences"] = person.pop("staff_preferences")
        return data

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
        
    # Dynamic inputs from JSON payload
    staff_members = payload.get("staff_data")
    if not staff_members:
        staff_members = fetch_staff()
        
    if not staff_members:
        print("No active staff found. Aborting.")
        return

    num_staff = len(staff_members)
    
    # Extract month/year/days from payload
    num_days = payload.get("days_in_month", 31)
    target_month = payload.get("month", datetime.date.today().month)
    target_year = payload.get("year", datetime.date.today().year)
    
    # 4 explicit shift types
    shifts = ["morning", "afternoon", "evening", "night"]
    num_shifts = len(shifts)

    # Build OR‑Tools model
    model = cp_model.CpModel()
    shift_vars = {}
    for s in range(num_staff):
        for d in range(num_days):
            for i in range(num_shifts):
                shift_vars[(s, d, i)] = model.NewBoolVar(f"shift_s{s}_d{d}_i{i}")

    # Constraint 1: Exactly 2 staff per shift
    staff_per_shift = 2
    for d in range(num_days):
        for i in range(num_shifts):
            model.Add(sum(shift_vars[(s, d, i)] for s in range(num_staff)) == staff_per_shift)

    # Constraint 2: At most one shift per staff per day
    for s in range(num_staff):
        for d in range(num_days):
            model.AddAtMostOne(shift_vars[(s, d, i)] for i in range(num_shifts))

    # Constraint 3: Respect max_shifts_per_month from data
    for s, person in enumerate(staff_members):
        max_shifts = int(person.get("max_shifts_per_month", 20))
        model.Add(
            sum(shift_vars[(s, d, i)] for d in range(num_days) for i in range(num_shifts))
            <= max_shifts
        )
        
    # Constraint 4: Ergonomic Rest Period (No Night -> Morning)
    night_idx = shifts.index("night")
    morning_idx = shifts.index("morning")
    for s in range(num_staff):
        for d in range(num_days - 1):
            model.Add(shift_vars[(s, d, night_idx)] + shift_vars[(s, d+1, morning_idx)] <= 1)
        
    # Objective Function: Balance Preference Matching against Fairness/Rotation
    W_pref = 100
    W_fairness = 10
    
    objective_terms = []
    for s, person in enumerate(staff_members):
        # Default historical counts
        hist_counts = person.get("historical_shift_counts", {})
        if not hist_counts or isinstance(hist_counts, str):
            try:
                if isinstance(hist_counts, str):
                    hist_counts = json.loads(hist_counts)
                else:
                    hist_counts = {}
            except Exception:
                hist_counts = {}
                
        # Map preferences
        prefs = person.get("preferences", [])
        pref_map = {p.get("preferred_shift_type") or p.get("shift_type"): p.get("weight", 1) or p.get("preference_weight", 1) for p in prefs if isinstance(p, dict)}
        
        for i, shift_name in enumerate(shifts):
            # historical count
            h_is = int(hist_counts.get(shift_name, 0))
            # preference
            p_is = int(pref_map.get(shift_name, 0))
            
            coeff = (W_pref * p_is) - (W_fairness * h_is)
            for d in range(num_days):
                objective_terms.append(coeff * shift_vars[(s, d, i)])
                
    # We want to maximize the score
    model.Maximize(sum(objective_terms))

    print("Matrix built. Solving constraints...")
    solver = cp_model.CpSolver()
    # Add a max time limit to prevent infinite searching
    solver.parameters.max_time_in_seconds = 30.0
    status = solver.Solve(model)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print(f"Optimal schedule found! Status: {solver.StatusName(status)}")
        # Construct exact dates using target_year and target_month
        try:
            start_date = datetime.date(target_year, target_month, 1)
        except ValueError:
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
            # Delete existing unlocked shifts for the month to prevent duplicates
            start_date_str = start_date.isoformat()
            end_date_str = (start_date + datetime.timedelta(days=num_days)).isoformat()
            supabase.table("fact_shifts").delete().gte("shift_date", start_date_str).lt("shift_date", end_date_str).eq("is_locked", False).execute()
            
            supabase.table("fact_shifts").insert(shift_records).execute()
            print(f"Success! Pushed {len(shift_records)} shifts to 'fact_shifts'.")
            
        # Log reasoning (simple text)
        log_text = (
            f"Successfully generated a {num_days}‑day monthly schedule for {target_year}-{target_month:02d} "
            f"with {num_staff} staff members, balancing preferences and historical fairness."
        )
        if not LOCAL_MODE:
            supabase.table("solver_logs").insert({"log_text": log_text}).execute()
    else:
        print("Failed: No feasible schedule found with given constraints.")

if __name__ == "__main__":
    solve_and_upload()