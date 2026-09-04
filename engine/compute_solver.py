from ortools.sat.python import cp_model

def solve_compute(payload: dict, job_id: str = None) -> dict:
    """
    Solves Cloud Compute Scheduling (Bin Packing) problems.
    payload expects:
    - servers: List of dicts with 'id', 'capacity'
    - workloads: List of dicts with 'id', 'weight'
    """
    try:
        servers = payload.get("servers", [])
        workloads = payload.get("workloads", [])
        
        if not servers or not workloads:
            return {"status": "failed", "message": "Missing servers or workloads data."}
            
        data = {
            "bin_capacities": [s.get("capacity", 100) for s in servers],
            "weights": [w.get("weight", 10) for w in workloads],
            "items": list(range(len(workloads))),
            "bins": list(range(len(servers))),
        }

        model = cp_model.CpModel()

        # Variables: x[i, j] = 1 if item i is packed in bin j.
        x = {}
        for i in data["items"]:
            for j in data["bins"]:
                x[(i, j)] = model.NewBoolVar(f"x_{i}_{j}")

        # Each item is assigned to exactly one bin.
        for i in data["items"]:
            model.AddExactlyOne(x[(i, j)] for j in data["bins"])

        # The amount packed in each bin cannot exceed its capacity.
        for j in data["bins"]:
            model.Add(
                sum(x[(i, j)] * data["weights"][i] for i in data["items"])
                <= data["bin_capacities"][j]
            )

        # Objective: minimize the number of bins used.
        # y[j] = 1 if bin j is used.
        y = {}
        for j in data["bins"]:
            y[j] = model.NewBoolVar(f"y_{j}")

        for i in data["items"]:
            for j in data["bins"]:
                model.Add(x[(i, j)] <= y[j])

        model.Minimize(sum(y[j] for j in data["bins"]))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30.0
        
        status = solver.Solve(model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            allocations = []
            for j in data["bins"]:
                if solver.Value(y[j]) == 1:
                    bin_items = []
                    for i in data["items"]:
                        if solver.Value(x[(i, j)]) == 1:
                            bin_items.append(workloads[i].get("id", str(i)))
                    allocations.append({
                        "server_id": servers[j].get("id", str(j)),
                        "workloads": bin_items
                    })
            return {"status": "completed", "servers_used": int(solver.ObjectiveValue()), "allocations": allocations}
        else:
            return {"status": "failed", "message": "No solution found."}

    except Exception as e:
        return {"status": "failed", "message": str(e)}
