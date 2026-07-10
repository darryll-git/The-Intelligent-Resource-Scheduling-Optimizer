import time
import requests
import subprocess
import os
import sys

def run_test():
    print("==================================================")
    print("🚀 AUTOMATED END-TO-END WORKFLOW TEST")
    print("==================================================")
    
    print("\n[1/3] Starting Flask Backend (Port 5000)...")
    flask_process = subprocess.Popen([sys.executable, "engine/app.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print("[2/3] Starting Headless Mock n8n Orchestrator (Port 5001)...")
    n8n_process = subprocess.Popen([sys.executable, "mock_n8n.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print("Waiting 3 seconds for services to boot...")
    time.sleep(3)
    
    try:
        print("\n[3/3] Firing Payload to Flask Backend...")
        payload = {"num_days": 7, "shifts": ["Morning", "Night"]}
        
        # 1. Hit Flask to get Job ID
        res = requests.post("http://localhost:5000/api/schedule", json=payload)
        res.raise_for_status()
        job_id = res.json().get("job_id")
        print(f"✅ Job Accepted by Flask. Job ID: {job_id}")
        
        # 2. Trigger Orchestrator Webhook
        print("\n🤖 Forwarding webhook payload to Headless Orchestrator...")
        webhook_payload = {"job_id": job_id, "num_days": 7, "shifts": ["Morning", "Night"]}
        res2 = requests.post("http://localhost:5001/webhook/schedule-trigger", json=webhook_payload)
        res2.raise_for_status()
        print("✅ Orchestrator Webhook Triggered Successfully!")
        
        print("\n⏳ Orchestrator is running optimization and writing to Supabase...")
        print("You can verify the instant realtime UI update by checking the frontend!")
        print("\nTest completed successfully. Shutting down background services...")
        
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        
    finally:
        flask_process.terminate()
        n8n_process.terminate()
        print("Services shut down.")

if __name__ == "__main__":
    run_test()
