import time
import requests
import subprocess
import os
import sys

def run_test():
    print("==================================================")
    print("AUTOMATED ASYNC WORKFLOW TEST")
    print("==================================================")
    
    print("\n[1/3] Starting Flask Backend (Port 5000)...")
    flask_process = subprocess.Popen([sys.executable, "engine/app.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    print("[2/3] Starting Headless Mock n8n Orchestrator (Port 5678)...")
    n8n_process = subprocess.Popen([sys.executable, "mock_n8n.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    print("Waiting 5 seconds for services to boot...")
    time.sleep(5)
    
    try:
        print("\n[3/3] Firing Payload to Flask Backend...")
        payload = {
            "month": 11, 
            "year": 2026,
            "webhook_url": "http://localhost:5678/webhook/schedule-complete"
        }
        
        headers = {
            "X-API-Key": os.getenv("API_SECRET_KEY", "super-secret-local-key")
        }
        
        # 1. Hit Flask to trigger async job
        res = requests.post("http://localhost:5000/api/schedule", json=payload, headers=headers)
        res.raise_for_status()
        job_id = res.json().get("job_id")
        print(f"[SUCCESS] Job Accepted by Flask asynchronously. Job ID: {job_id}")
        
        # 2. Wait for background thread to run solver and trigger webhook
        print("\nWaiting 10 seconds for background solver execution and webhook callback...")
        time.sleep(10)
        
        # We will check n8n's stdout after terminating
        print("\nTest completed successfully. Shutting down background services...")
        
    except Exception as e:
        print(f"\n[FAILED] Test Failed: {e}")
        
    finally:
        flask_process.terminate()
        n8n_process.terminate()
        
        flask_out, flask_err = flask_process.communicate()
        n8n_out, n8n_err = n8n_process.communicate()
        
        if "Received webhook for Job ID" in n8n_out:
            print("[SUCCESS] Verified Orchestrator Webhook was triggered successfully!")
        else:
            print("[FAILED] Orchestrator did NOT receive the webhook.")
            print("n8n output:")
            print(n8n_out)
        
        if flask_err: print(f"\n--- FLASK ERROR LOG ---\n{flask_err}")
        if n8n_err: print(f"\n--- N8N ERROR LOG ---\n{n8n_err}")
        
        print("\nServices shut down.")

if __name__ == "__main__":
    run_test()
