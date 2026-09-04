from ortools.sat.python import cp_model

def solve_manufacturing(payload: dict, job_id: str = None) -> dict:
    """
    Solves Job Shop Scheduling problems.
    payload expects:
    - jobs: List of jobs, where each job is a list of (machine_id, processing_time) tuples.
    """
    try:
        jobs_data = payload.get("jobs", [])
        if not jobs_data:
            return {"status": "failed", "message": "Missing jobs data."}

        model = cp_model.CpModel()
        
        # Determine number of machines by finding max machine_id
        machines_count = 1 + max(task[0] for job in jobs_data for task in job)
        all_machines = range(machines_count)
        
        horizon = sum(task[1] for job in jobs_data for task in job)

        all_tasks = {}
        machine_to_intervals = {machine: [] for machine in all_machines}

        for job_id_idx, job in enumerate(jobs_data):
            for task_id_idx, task in enumerate(job):
                machine = task[0]
                duration = task[1]
                suffix = f"_{job_id_idx}_{task_id_idx}"
                
                start_var = model.NewIntVar(0, horizon, "start" + suffix)
                end_var = model.NewIntVar(0, horizon, "end" + suffix)
                interval_var = model.NewIntervalVar(start_var, duration, end_var, "interval" + suffix)
                
                all_tasks[job_id_idx, task_id_idx] = {
                    "start": start_var,
                    "end": end_var,
                    "interval": interval_var,
                }
                machine_to_intervals[machine].append(interval_var)

        # Create and add disjunctive constraints (no overlap on machines).
        for machine in all_machines:
            model.AddNoOverlap(machine_to_intervals[machine])

        # Precedences inside a job.
        for job_id_idx, job in enumerate(jobs_data):
            for task_id_idx in range(len(job) - 1):
                model.Add(
                    all_tasks[job_id_idx, task_id_idx + 1]["start"]
                    >= all_tasks[job_id_idx, task_id_idx]["end"]
                )

        # Makespan objective.
        obj_var = model.NewIntVar(0, horizon, "makespan")
        model.AddMaxEquality(
            obj_var,
            [all_tasks[job_id_idx, len(job) - 1]["end"] for job_id_idx, job in enumerate(jobs_data)],
        )
        model.Minimize(obj_var)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30.0
        
        status = solver.Solve(model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            result = []
            for job_id_idx, job in enumerate(jobs_data):
                for task_id_idx, task in enumerate(job):
                    machine = task[0]
                    start = solver.Value(all_tasks[job_id_idx, task_id_idx]["start"])
                    result.append({
                        "job": job_id_idx,
                        "task": task_id_idx,
                        "machine": machine,
                        "start": start,
                        "duration": task[1]
                    })
            return {"status": "completed", "makespan": solver.ObjectiveValue(), "schedule": result}
        else:
            return {"status": "failed", "message": "No solution found."}

    except Exception as e:
        return {"status": "failed", "message": str(e)}
