import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Supabase credentials not found in .env file.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Path to local staff data
base_dir = os.path.dirname(__file__)
staff_data_path = os.path.join(base_dir, "engine", "staff_data.json")

def migrate_staff_data():
    try:
        with open(staff_data_path, "r", encoding="utf-8") as f:
            staff_data = json.load(f)
            
        print(f"Found {len(staff_data)} staff records in local JSON. Migrating to Supabase 'dim_staff' table...")
        
        # Insert data into Supabase
        response = supabase.table("dim_staff").upsert(staff_data).execute()
        
        print("Successfully migrated staff data!")
        print("Response:", response.data)
    except Exception as e:
        print(f"Failed to migrate staff data: {e}")

if __name__ == "__main__":
    migrate_staff_data()
