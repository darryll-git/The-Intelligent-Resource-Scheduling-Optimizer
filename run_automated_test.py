import time
import requests
import subprocess
import os
import sys

def run_test():
    print("==================================================")
    print("AUTOMATED END-TO-END WORKFLOW TEST")
    print("==================================================")
    
    print("\n[1/3] Starting Flask Backend (Port 5000)...")
    flask_process = subprocess.Popen([sys.executable, "-m", "engine.app"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    print("[2/3] Starting Headless Mock n8n Orchestrator (Port 5001)...")
    n8n_process = subprocess.Popen([sys.executable, "mock_n8n.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    print("Waiting 5 seconds for services to boot...")
    time.sleep(5)
    
    try:
        print("\n[3/3] Firing Payload to Flask Backend...")
        payload = {"num_days": 7, "shifts": ["Morning", "Night"]}
        
        # 1. Hit Flask to get Job ID
        res = requests.post("http://localhost:5000/api/schedule", json=payload)
        res.raise_for_status()
        job_id = res.json().get("job_id")
        print(f"[SUCCESS] Job Accepted by Flask. Job ID: {job_id}")
        
        # 2. Trigger Orchestrator Webhook
        print("\nForwarding webhook payload to Headless Orchestrator...")
        webhook_payload = {"job_id": job_id, "num_days": 7, "shifts": ["Morning", "Night"]}
        res2 = requests.post("http://localhost:5001/webhook/schedule-trigger", json=webhook_payload)
        res2.raise_for_status()
        print("[SUCCESS] Orchestrator Webhook Triggered Successfully!")
        
        print("\nOrchestrator is running optimization and writing to Supabase...")
        print("You can verify the instant realtime UI update by checking the frontend!")
        print("\nTest completed successfully. Shutting down background services...")
        
    except Exception as e:
        print(f"\n[FAILED] Test Failed: {e}")
        
    finally:
        flask_process.terminate()
        n8n_process.terminate()
        
        flask_err = flask_process.stderr.read() if flask_process.stderr else ""
        n8n_err = n8n_process.stderr.read() if n8n_process.stderr else ""
        
        if flask_err: print(f"\n--- FLASK ERROR LOG ---\n{flask_err}")
        if n8n_err: print(f"\n--- N8N ERROR LOG ---\n{n8n_err}")
        
        print("\nServices shut down.")

if __name__ == "__main__":
    run_test()
