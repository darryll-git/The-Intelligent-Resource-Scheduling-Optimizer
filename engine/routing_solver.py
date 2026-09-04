from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import json

def solve_routing(payload: dict, job_id: str = None) -> dict:
    """
    Solves the Vehicle Routing Problem (VRP) using OR-Tools.
    Expected payload structure:
    - distance_matrix: 2D array of distances
    - num_vehicles: int
    - depot: int
    """
    try:
        data = {
            "distance_matrix": payload.get("distance_matrix", []),
            "num_vehicles": payload.get("num_vehicles", 1),
            "depot": payload.get("depot", 0),
        }
        
        if not data["distance_matrix"]:
            return {"status": "failed", "message": "Missing distance_matrix."}

        manager = pywrapcp.RoutingIndexManager(
            len(data["distance_matrix"]), data["num_vehicles"], data["depot"]
        )
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data["distance_matrix"][from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        # Apply time limit for free tier
        search_parameters.time_limit.seconds = 30

        solution = routing.SolveWithParameters(search_parameters)

        if solution:
            routes = []
            for vehicle_id in range(data["num_vehicles"]):
                index = routing.Start(vehicle_id)
                route = []
                while not routing.IsEnd(index):
                    route.append(manager.IndexToNode(index))
                    index = solution.Value(routing.NextVar(index))
                route.append(manager.IndexToNode(index))
                routes.append(route)
            
            return {"status": "completed", "routes": routes, "message": "Optimal routing found."}
        else:
            return {"status": "failed", "message": "No solution found."}

    except Exception as e:
        return {"status": "failed", "message": str(e)}
