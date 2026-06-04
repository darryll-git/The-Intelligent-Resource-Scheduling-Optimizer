import sys
import os
import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

# Add parent directory to path so we can import engine
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.solver import solve_schedule

app = Flask(__name__)
CORS(app)

@app.route('/api/optimize', methods=['POST'])
def optimize_schedule():
    """
    Accepts staff availability payload, runs solver, returns optimized schedule.
    """
    data = request.json or {}
    
    try:
        schedule = solve_schedule()
        if schedule:
            return jsonify({"status": "success", "data": schedule}), 200
        else:
            return jsonify({"status": "error", "message": "No feasible schedule found"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/validate_shift', methods=['POST'])
def validate_shift():
    """
    Validates a manual shift change to ensure it doesn't break hard constraints.
    Expects JSON: { "staff_id": "...", "date": "...", "shift_type": "...", "current_schedule": [...] }
    """
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400
    
    staff_id = data.get("staff_id")
    target_date = data.get("date")
    current_schedule = data.get("current_schedule", [])
    
    # Find all shifts assigned to this staff member
    staff_shifts = [s for s in current_schedule if s.get("staff_id") == staff_id]
    
    # Constraint: max 5 shifts per week (will be dynamic later)
    if len(staff_shifts) > 5:
        return jsonify({"valid": False, "reason": "Exceeds maximum weekly shifts"}), 200
        
    # Constraint: at most 1 shift per day
    same_day_shifts = [s for s in staff_shifts if s.get("shift_date") == target_date]
    if len(same_day_shifts) > 1: # >1 because the dropped shift is already in current_schedule
        return jsonify({"valid": False, "reason": "Already working a shift on this day"}), 200
        
    return jsonify({"valid": True}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
