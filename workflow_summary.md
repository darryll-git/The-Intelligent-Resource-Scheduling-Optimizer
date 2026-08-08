# The Intelligent Resource & Scheduling Optimizer

## Project Summary

The Intelligent Resource & Scheduling Optimizer is an end-to-end scheduling and logistics tool designed to compute mathematically optimal resource allocations (such as staff shifts) based on business constraints and individual staff preferences. 

The core of the system is a Python engine powered by **Google OR-Tools** (Constraint Programming), which formulates and solves a linear programming problem to assign staff to specific shifts.

### Key Features
1. **Local or Cloud Execution**: Can run entirely locally (using JSON files for input/output data) without any external dependencies, or it can be configured to connect to a **Supabase** backend for cloud data storage and retrieval.
2. **Deterministic Optimization**: Uses constraint satisfaction to strictly enforce rules like:
   - Exactly 2 staff members per shift.
   - At most 1 shift per staff member per day.
   - Respecting maximum shifts per month per staff member.
   - Ergonomic rest periods (e.g., no night shifts followed immediately by morning shifts).
3. **Objective Balancing**: Incorporates an objective function that balances matching staff to their preferred shifts against historical fairness (ensuring equitable distribution of less desirable shifts).
4. **Lightweight Frontend (Optional)**: A React-based frontend that can consume the generated schedules for visualization by stakeholders.

## System Workflow

Below is a detailed flowchart explaining how the components of the system connect and where data flows during execution:

```mermaid
flowchart TD
    %% Define Styles
    classDef input fill:#f9d0c4,stroke:#333,stroke-width:2px;
    classDef process fill:#d4e157,stroke:#333,stroke-width:2px;
    classDef decision fill:#fff59d,stroke:#333,stroke-width:2px;
    classDef output fill:#81d4fa,stroke:#333,stroke-width:2px;
    classDef ui fill:#ce93d8,stroke:#333,stroke-width:2px;

    %% Nodes
    A1[Local Mode\nengine/staff_data.json]:::input
    A2[Supabase Mode\ndim_staff table & preferences]:::input
    B{Configuration Mode\nLOCAL_MODE = True/False?}:::decision
    
    C[engine/solver.py\nFetch Staff Data & Constraints]:::process
    
    D[Build OR-Tools CP Model]:::process
    
    E1[Constraint 1: 2 Staff / Shift]:::process
    E2[Constraint 2: Max 1 Shift / Day]:::process
    E3[Constraint 3: Max Shifts / Month]:::process
    E4[Constraint 4: Ergonomic Rest\nNo Night -> Morning]:::process
    
    F[Objective Function:\nMaximize (Preferences - Historical Fairness)]:::process
    
    G[CP Solver Solves Matrix\nMax Time: 30s]:::process
    
    H{Status: Optimal/Feasible?}:::decision
    
    I1[Fail: No feasible schedule]:::output
    I2[Generate Shift Records List]:::process
    
    J{Write Mode}:::decision
    
    K1[Local Mode\nengine/schedule_output.json]:::output
    K2[Local Mode\nfrontend/public/schedule.json]:::output
    K3[Supabase Mode\nfact_shifts table]:::output
    K4[Supabase Mode\nsolver_logs table]:::output
    
    L[React Frontend UI\nDisplays final schedule]:::ui

    %% Edges
    B -- True --> A1
    B -- False --> A2
    A1 --> C
    A2 --> C
    
    C --> D
    D --> E1 & E2 & E3 & E4
    E1 & E2 & E3 & E4 --> F
    F --> G
    
    G --> H
    H -- No --> I1
    H -- Yes --> I2
    
    I2 --> J
    J -- Local --> K1
    J -- Local --> K2
    J -- Supabase --> K3
    J -- Supabase --> K4
    
    K2 -.->|Consumed by| L
    K3 -.->|Fetched by| L
```

### Detailed Workflow Explanation

1. **Initialization & Data Fetching**: 
   - When the `engine/solver.py` script is executed, it first determines if it is running in **Local Mode** or **Supabase Mode** based on CLI arguments (`--local`) or environment variables.
   - It then fetches the staff definitions, historical shift counts, and staff shift preferences either from the local `engine/staff_data.json` or the Supabase `dim_staff` table.

2. **Model Construction**:
   - The OR-Tools `CpModel` is initialized. Boolean variables are created for every combination of `(staff_member, day, shift_type)`.
   - Four primary **hard constraints** are applied to the model: ensuring shift coverage (2 per shift), avoiding double-booking in a single day, respecting monthly maximums, and ensuring adequate rest between shifts.

3. **Objective Optimization**:
   - The model defines an objective function to **maximize**. It assigns a positive weight to matching staff members with their preferred shifts, and a negative penalty based on how often they historically worked that shift (to ensure fair rotation).

4. **Solving**:
   - The CP solver attempts to find an optimal or feasible schedule within a 30-second time limit.

5. **Output Generation**:
   - If a feasible schedule is found, the boolean matrices are translated into an array of readable shift records.
   - **Local Mode**: The data is exported to `engine/schedule_output.json`. If a frontend directory exists, it also creates a copy at `frontend/public/schedule.json` so the local React app can immediately serve it.
   - **Supabase Mode**: Unlocked shifts for the target month are cleared from the `fact_shifts` table, the new shifts are inserted, and a success message is written to the `solver_logs` table.
   - The **React Frontend** then consumes this generated JSON or fetches from Supabase to render the schedule visually to end-users.
