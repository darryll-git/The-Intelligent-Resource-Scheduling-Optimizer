import os
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from solver import solve_and_upload

app = Flask(__name__)
CORS(app) # Enable CORS for frontend communication

@app.route("/api/schedule", methods=["POST"])
def trigger_schedule():
    """
    Endpoint to trigger the scheduling engine.
    Now instantly returns 202 Accepted. The actual orchestration 
    is handed off to n8n which will call /api/internal/solve.
    """
    payload = request.json or {}
    job_id = str(uuid.uuid4())
    
    # In a fully decoupled architecture, the frontend might call the n8n webhook directly 
    # and bypass this, or this endpoint could forward the request to n8n.
    # For now, we simply validate the request and return a 202 as requested.
    return jsonify({
        "job_id": job_id, 
        "status": "accepted",
        "message": "Job accepted. Orchestration will be handled by n8n."
    }), 202

@app.route("/api/internal/solve", methods=["POST"])
def internal_solve():
    """
    Synchronous endpoint called by the n8n orchestrator.
    Executes the optimization engine and returns the result.
    """
    try:
        # Pass payload to solver if needed in the future
        payload = request.json or {}
        
        # Synchronously execute the solver
        solve_and_upload(payload)
        
        return jsonify({
            "status": "success",
            "message": "Optimization finished successfully."
        }), 200
    except Exception as e:
        return jsonify({
            "status": "failed",
            "error": str(e)
        }), 500

@app.route("/api/shifts", methods=["GET"])
def get_shifts():
    """Fetch the latest schedule from Supabase (or local JSON)."""
    try:
        from solver import LOCAL_MODE, supabase, fetch_staff
        if LOCAL_MODE:
            import json, os
            base_dir = os.path.dirname(__file__)
            frontend_path = os.path.join(os.path.dirname(base_dir), "frontend", "public", "schedule.json")
            if os.path.exists(frontend_path):
                with open(frontend_path, "r", encoding="utf-8") as f:
                    return jsonify(json.load(f)), 200
            return jsonify([]), 200
        else:
            # Fetch up to 1000 shifts from Supabase
            response = supabase.table("fact_shifts").select("*").order("created_at", desc=True).limit(1000).execute()
            # The data is sorted descending by created_at, but we might want them in order of shift_date
            sorted_data = sorted(response.data, key=lambda x: (x.get('shift_date', ''), x.get('shift_type', '')))
            return jsonify(sorted_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Run locally on port 5000
    app.run(host="0.0.0.0", port=5000, debug=True)
