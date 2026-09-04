import os
import uuid
import datetime
import json
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, Dict, Any

try:
    from supabase import create_client, Client
except ImportError:
    Client = None

app = FastAPI(title="Scheduling Optimizer API")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")  # Token required to access this private space

def get_supabase() -> Optional[Client]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def verify_token(authorization: Optional[str] = Header(None)):
    """Verify Hugging Face Authorization token to protect the API."""
    if not HF_TOKEN:
        # If no token is set in env, we might be running locally, but in prod we should enforce it.
        return True
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = authorization.split("Bearer ")[1]
    if token != HF_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid token")

@app.get("/health")
def health_check():
    """Endpoint for cron-job.org to ping and prevent container hibernation."""
    return {"status": "awake", "time": datetime.datetime.utcnow().isoformat()}

class SolveRequest(BaseModel):
    is_sandbox: bool = False
    payload: Dict[str, Any]
    tenant_id: str

def run_workforce_solver_background(job_id: str, request: SolveRequest):
    """Background task to run the workforce solver and push results to Supabase."""
    supabase = get_supabase()
    if not supabase:
        print(f"[Job {job_id}] Supabase not configured. Cannot update status.")
        return

    from engine.workforce_solver import solve_and_upload
    
    print(f"[Job {job_id}] Starting workforce solver... (sandbox={request.is_sandbox})")
    
    try:
        # Call the actual solver engine
        result = solve_and_upload(payload=request.payload, job_id=job_id)
        
        # Determine status based on solver result
        status = "COMPLETED"
        if result and isinstance(result, dict) and result.get("status") == "failed":
            status = "FAILED"
            
        supabase.table("jobs").update({
            "status": status,
            "result_summary": result.get("message", "Solver finished.") if isinstance(result, dict) else "Solver completed.",
            "completed_at": datetime.datetime.utcnow().isoformat()
        }).eq("id", job_id).execute()
        
        print(f"[Job {job_id}] {status}.")

        
    except Exception as e:
        print(f"[Job {job_id}] Failed: {e}")
        supabase.table("jobs").update({
            "status": "FAILED",
            "result_summary": str(e),
            "completed_at": datetime.datetime.utcnow().isoformat()
        }).eq("id", job_id).execute()


@app.post("/api/solve/workforce", status_code=202)
def solve_workforce(request: SolveRequest, background_tasks: BackgroundTasks, auth_ok: bool = Depends(verify_token)):
    """Async endpoint to trigger workforce scheduling."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    job_id = str(uuid.uuid4())
    
    # Create PENDING job in DB
    try:
        supabase.table("jobs").insert({
            "id": job_id,
            "tenant_id": request.tenant_id,
            "job_type": "workforce",
            "status": "PENDING",
            "is_sandbox": request.is_sandbox,
            "created_at": datetime.datetime.utcnow().isoformat()
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create job record: {e}")

    # Enqueue background task
    background_tasks.add_task(run_workforce_solver_background, job_id, request)

# Return immediately
    return {"job_id": job_id, "status": "PENDING", "message": "Workforce solver started in background."}


def run_routing_solver_background(job_id: str, request: SolveRequest):
    supabase = get_supabase()
    from engine.routing_solver import solve_routing
    print(f"[Job {job_id}] Starting routing solver...")
    try:
        result = solve_routing(payload=request.payload, job_id=job_id)
        status = "COMPLETED" if result.get("status") != "failed" else "FAILED"
        if supabase:
            supabase.table("jobs").update({
                "status": status,
                "result_summary": json.dumps(result),
                "completed_at": datetime.datetime.utcnow().isoformat()
            }).eq("id", job_id).execute()
        print(f"[Job {job_id}] {status}.")
    except Exception as e:
        if supabase:
            supabase.table("jobs").update({"status": "FAILED", "result_summary": str(e)}).eq("id", job_id).execute()


@app.post("/api/solve/routing", status_code=202)
def solve_routing_endpoint(request: SolveRequest, background_tasks: BackgroundTasks, auth_ok: bool = Depends(verify_token)):
    job_id = str(uuid.uuid4())
    supabase = get_supabase()
    if supabase:
        supabase.table("jobs").insert({"id": job_id, "tenant_id": request.tenant_id, "job_type": "routing", "status": "PENDING"}).execute()
    background_tasks.add_task(run_routing_solver_background, job_id, request)
    return {"job_id": job_id, "status": "PENDING", "message": "Routing solver started in background."}


def run_manufacturing_solver_background(job_id: str, request: SolveRequest):
    supabase = get_supabase()
    from engine.manufacturing_solver import solve_manufacturing
    print(f"[Job {job_id}] Starting manufacturing solver...")
    try:
        result = solve_manufacturing(payload=request.payload, job_id=job_id)
        status = "COMPLETED" if result.get("status") != "failed" else "FAILED"
        if supabase:
            supabase.table("jobs").update({
                "status": status,
                "result_summary": json.dumps(result),
                "completed_at": datetime.datetime.utcnow().isoformat()
            }).eq("id", job_id).execute()
        print(f"[Job {job_id}] {status}.")
    except Exception as e:
        if supabase:
            supabase.table("jobs").update({"status": "FAILED", "result_summary": str(e)}).eq("id", job_id).execute()


@app.post("/api/solve/manufacturing", status_code=202)
def solve_manufacturing_endpoint(request: SolveRequest, background_tasks: BackgroundTasks, auth_ok: bool = Depends(verify_token)):
    job_id = str(uuid.uuid4())
    supabase = get_supabase()
    if supabase:
        supabase.table("jobs").insert({"id": job_id, "tenant_id": request.tenant_id, "job_type": "manufacturing", "status": "PENDING"}).execute()
    background_tasks.add_task(run_manufacturing_solver_background, job_id, request)
    return {"job_id": job_id, "status": "PENDING", "message": "Manufacturing solver started in background."}


def run_compute_solver_background(job_id: str, request: SolveRequest):
    supabase = get_supabase()
    from engine.compute_solver import solve_compute
    print(f"[Job {job_id}] Starting compute solver...")
    try:
        result = solve_compute(payload=request.payload, job_id=job_id)
        status = "COMPLETED" if result.get("status") != "failed" else "FAILED"
        if supabase:
            supabase.table("jobs").update({
                "status": status,
                "result_summary": json.dumps(result),
                "completed_at": datetime.datetime.utcnow().isoformat()
            }).eq("id", job_id).execute()
        print(f"[Job {job_id}] {status}.")
    except Exception as e:
        if supabase:
            supabase.table("jobs").update({"status": "FAILED", "result_summary": str(e)}).eq("id", job_id).execute()


@app.post("/api/solve/compute", status_code=202)
def solve_compute_endpoint(request: SolveRequest, background_tasks: BackgroundTasks, auth_ok: bool = Depends(verify_token)):
    job_id = str(uuid.uuid4())
    supabase = get_supabase()
    if supabase:
        supabase.table("jobs").insert({"id": job_id, "tenant_id": request.tenant_id, "job_type": "compute", "status": "PENDING"}).execute()
    background_tasks.add_task(run_compute_solver_background, job_id, request)
    return {"job_id": job_id, "status": "PENDING", "message": "Compute solver started in background."}


