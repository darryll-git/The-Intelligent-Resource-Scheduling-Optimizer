import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv(".env")
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if url and key:
    supabase: Client = create_client(url, key)
    res = supabase.table("fact_shifts").select("*").order("shift_date", desc=False).execute()
    dates = sorted(list(set([r["shift_date"][:10] for r in res.data])))
    print("Unique shift dates in DB:", dates)
    print("Total shifts in DB:", len(res.data))
    
    # Check solver logs
    logs = supabase.table("solver_logs").select("*").order("created_at", desc=True).limit(2).execute()
    for log in logs.data:
        print("Log:", log["log_text"])
else:
    print("No supabase credentials found.")
