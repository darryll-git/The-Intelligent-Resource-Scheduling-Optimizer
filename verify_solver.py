import sys
import os

# Add engine to path
sys.path.append(os.path.join(os.path.dirname(__file__), "engine"))
from engine.solver import solve_and_upload

# Mock Payload for 30-day month
payload = {
    "month": 9,
    "year": 2026,
    "days_in_month": 30,
    "staff_data": [
        {
            "staff_id": "EMP001",
            "max_shifts_per_month": 25,
            "historical_shift_counts": {"morning": 5, "afternoon": 0, "evening": 0, "night": 0},
            "preferences": [{"shift_type": "morning", "weight": 5}]
        },
        {
            "staff_id": "EMP002",
            "max_shifts_per_month": 25,
            "historical_shift_counts": {"morning": 1, "afternoon": 0, "evening": 0, "night": 0},
            "preferences": [{"shift_type": "morning", "weight": 5}]
        },
        {
            "staff_id": "EMP003",
            "max_shifts_per_month": 25,
            "historical_shift_counts": {"morning": 0, "afternoon": 0, "evening": 0, "night": 0},
            "preferences": []
        },
        {
            "staff_id": "EMP004",
            "max_shifts_per_month": 25,
            "historical_shift_counts": {"morning": 0, "afternoon": 0, "evening": 0, "night": 0},
            "preferences": []
        },
        {
            "staff_id": "EMP005",
            "max_shifts_per_month": 25,
            "historical_shift_counts": {"morning": 0, "afternoon": 0, "evening": 0, "night": 0},
            "preferences": []
        },
        {
            "staff_id": "EMP006",
            "max_shifts_per_month": 25,
            "historical_shift_counts": {"morning": 0, "afternoon": 0, "evening": 0, "night": 0},
            "preferences": []
        }
    ]
}

if __name__ == "__main__":
    print("Running verification for Monthly 4-Shift Scheduling (Local Mode)...")
    # Forcing LOCAL_MODE for the solver
    import engine.solver
    engine.solver.LOCAL_MODE = True
    
    solve_and_upload(payload)
    
    # Check the output JSON to verify who got the first morning shift
    import json
    with open("engine/schedule_output.json", "r") as f:
        schedule = json.load(f)
        
    morning_day1 = [s for s in schedule if s["shift_date"].startswith("2026-09-01") and s["shift_type"] == "morning"]
    print("\nMorning shift on Day 1 assigned to:", morning_day1[0]["staff_id"] if morning_day1 else "None")
    
    # EMP002 should get it over EMP001 because EMP002 has a lower historical count for morning,
    # and they both have equal preference weight for morning.
