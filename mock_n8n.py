import os
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/webhook/schedule-complete", methods=["POST"])
def webhook():
    """
    Mock n8n webhook endpoint. 
    Receives the final result of the asynchronous solver execution.
    """
    payload = request.json or {}
    job_id = payload.get("job_id")
    status = payload.get("status")
    
    if not job_id or not status:
        print("[n8n Mock] Bad Request: Missing job_id or status")
        return jsonify({"error": "Missing job_id or status"}), 400
        
    print(f"\n[n8n Mock] Received webhook for Job ID: {job_id}")
    print(f"[n8n Mock] Final Status: {status}")
    print(f"[n8n Mock] Details: {payload.get('details', 'No details provided.')}")
    
    if status == "completed":
        print("[n8n Mock] Workflow Step: Sending Success Emails to Staff... (Mocked)")
    else:
        print("[n8n Mock] Workflow Step: Alerting Admin of Scheduling Failure... (Mocked)")

    return jsonify({"success": True, "message": "Orchestrator received the payload successfully"}), 200

if __name__ == "__main__":
    print("Starting Mock n8n Orchestrator on port 5678...")
    app.run(host="0.0.0.0", port=5678, debug=True)
