import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Optional Supabase import
try:
    from supabase import create_client, Client
except ImportError:
    Client = None

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY and Client:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
CORS(app)

@app.route("/webhook/schedule-trigger", methods=["POST"])
def webhook():
    """
    Mock n8n webhook endpoint. 
    1. Receives job_id from frontend.
    2. Calls the synchronous backend solver.
    3. Writes success/failure to Supabase to trigger frontend websockets.
    """
    payload = request.json or {}
    job_id = payload.get("job_id", "unknown-job-id")
    
    print(f"[n8n Mock] Received webhook for Job ID: {job_id}")
    print("[n8n Mock] Calling synchronous solver api: /api/internal/solve")
    
    try:
        # Call the Flask backend solver API
        solve_res = requests.post("http://localhost:5000/api/internal/solve", json=payload, timeout=30)
        
        if solve_res.status_code == 200:
            print("[n8n Mock] Solve successful! Writing 'completed' status to Supabase solver_logs...")
            if supabase:
                import json
                supabase.table("solver_logs").insert({
                    "log_text": json.dumps({
                        "job_id": job_id,
                        "status": "completed",
                        "message": "Optimization completed successfully."
                    })
                }).execute()
        else:
            print("[n8n Mock] Solve failed! Writing 'failed' status to Supabase...")
            if supabase:
                import json
                supabase.table("solver_logs").insert({
                    "log_text": json.dumps({
                        "job_id": job_id,
                        "status": "failed",
                        "error_message": solve_res.text
                    })
                }).execute()
                
    except Exception as e:
        print(f"[n8n Mock] Error connecting to solver API: {e}")
        if supabase:
            import json
            supabase.table("solver_logs").insert({
                "log_text": json.dumps({
                    "job_id": job_id,
                    "status": "failed",
                    "error_message": str(e)
                })
            }).execute()

    # The webhook returns 200 OK immediately, but n8n continues in background (here we just did it synchronously for testing)
    return jsonify({"success": True}), 200

if __name__ == "__main__":
    print("Starting Mock n8n Orchestrator on port 5678...")
    app.run(host="0.0.0.0", port=5678, debug=True)
