import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "engine"))
import engine.solver
engine.solver.LOCAL_MODE = False
engine.solver.solve_and_upload({"month": 7, "year": 2026, "days_in_month": 31})
