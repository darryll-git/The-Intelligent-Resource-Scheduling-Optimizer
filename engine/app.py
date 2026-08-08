import os
import uuid
import threading
import requests
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from solver import solve_and_upload
from models import ScheduleRequestPayload, get_default_shifts
from pydantic import ValidationError
app = Flask(__name__)
CORS(app) # Enable CORS for frontend communication

API_SECRET_KEY = os.getenv("API_SECRET_KEY", "super-secret-local-key")

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        key = request.headers.get("X-API-Key")
        if key and key == API_SECRET_KEY:
            return f(*args, **kwargs)
        return jsonify({"error": "Unauthorized", "message": "Invalid or missing API key"}), 401
    return decorated_function

@app.route("/api/schedule", methods=["POST"])
@require_api_key
def trigger_schedule():
    """
    Endpoint to trigger the scheduling engine asynchronously.
    Returns 202 Accepted. The solver runs in the background and calls the webhook on completion.
    """
    payload = request.json or {}
    try:
        validated_payload = ScheduleRequestPayload(**payload)
        if not validated_payload.shifts:
            validated_payload.shifts = get_default_shifts()
        valid_dict = validated_payload.model_dump() if hasattr(validated_payload, "model_dump") else validated_payload.dict()
    except ValidationError as ve:
        return jsonify({
            "status": "failed",
            "error": "Validation Error",
            "details": ve.errors()
        }), 400

    job_id = str(uuid.uuid4())
    webhook_url = getattr(validated_payload, 'webhook_url', None)
    
    # Start the background task
    threading.Thread(target=run_solver_async, args=(valid_dict, job_id, webhook_url)).start()
    
    return jsonify({
        "job_id": job_id, 
        "status": "accepted",
        "message": "Job accepted. Optimization is running in the background."
    }), 202

def run_solver_async(payload, job_id, webhook_url):
    try:
        print(f"[Async Job {job_id}] Starting solver in background...")
        result = solve_and_upload(payload, job_id=job_id)
        
        if webhook_url:
            print(f"[Async Job {job_id}] Solver finished. Firing webhook to {webhook_url}")
            requests.post(webhook_url, json={
                "job_id": job_id,
                "status": result.get("status", "unknown") if result else "unknown",
                "details": result.get("message", "") if result else ""
            }, timeout=10)
    except Exception as e:
        print(f"[Async Job {job_id}] Unhandled exception in background thread: {e}")
        if webhook_url:
            try:
                requests.post(webhook_url, json={
                    "job_id": job_id,
                    "status": "failed",
                    "details": str(e)
                }, timeout=10)
            except Exception as webhook_e:
                print(f"[Async Job {job_id}] Failed to fire error webhook: {webhook_e}")

@app.route("/api/internal/solve", methods=["POST"])
@require_api_key
def internal_solve():
    """
    Synchronous endpoint called by the n8n orchestrator.
    Executes the optimization engine and returns the result.
    """
    try:
        # Pass payload to solver if needed in the future
        payload = request.json or {}
        
        try:
            validated_payload = ScheduleRequestPayload(**payload)
            if not validated_payload.shifts:
                validated_payload.shifts = get_default_shifts()
            valid_dict = validated_payload.model_dump() if hasattr(validated_payload, "model_dump") else validated_payload.dict()
        except ValidationError as ve:
            return jsonify({
                "status": "failed",
                "error": "Validation Error",
                "details": ve.errors()
            }), 400
        
        # Synchronously execute the solver
        solve_and_upload(valid_dict)
        
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
@require_api_key
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
