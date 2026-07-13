import csv
import random
import os
from datetime import datetime, timedelta

def generate_data():
    num_employees = 50
    roles = ["Manager", "Senior", "Junior", "Trainee"]
    role_weights = [0.1, 0.3, 0.4, 0.2]
    
    # Generate dates for the next 14 days to be used as potential vacation days
    start_date = datetime.today()
    future_dates = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(14)]
    
    data = []
    for i in range(1, num_employees + 1):
        staff_id = f"EMP_{i:03d}"
        first_names = ["John", "Jane", "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Heidi", "Ivan", "Judy"]
        last_names = ["Smith", "Doe", "Johnson", "Brown", "Williams", "Jones", "Miller", "Davis", "Garcia", "Rodriguez"]
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        
        role = random.choices(roles, weights=role_weights)[0]
        
        # 80% Full-time, 20% Part-time
        employment_type = random.choices(["Full-time", "Part-time"], weights=[0.8, 0.2])[0]
        
        if employment_type == "Full-time":
            max_shifts_per_week = 5
        else:
            max_shifts_per_week = random.choice([2, 3])
            
        # 30% chance of having 1-2 requested days off in the next 14 days
        vacation_days = ""
        if random.random() < 0.3:
            num_days_off = random.randint(1, 2)
            vacation_days = ";".join(random.sample(future_dates, num_days_off))
            
        data.append({
            "staff_id": staff_id,
            "name": name,
            "role": role,
            "employment_type": employment_type,
            "max_shifts_per_week": max_shifts_per_week,
            "vacation_days": vacation_days
        })
        
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(os.path.dirname(output_dir), "staff_roster.csv")
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["staff_id", "name", "role", "employment_type", "max_shifts_per_week", "vacation_days"])
        writer.writeheader()
        writer.writerows(data)
        
    print(f"Successfully generated {num_employees} synthetic employee records at {output_path}")

if __name__ == "__main__":
    generate_data()
