import json

def update_workflow():
    workflow_path = "n8n/orchestrator_workflow.json"
    with open(workflow_path, "r") as f:
        workflow = json.load(f)
        
    nodes = workflow["nodes"]
    connections = workflow["connections"]
    
    # Remove CSV nodes
    nodes = [n for n in nodes if n["name"] not in ["Read CSV", "Extract CSV", "Aggregate"]]
    workflow["nodes"] = nodes
    
    # Update Call Flask API Node
    for node in nodes:
        if node["name"] == "Call Flask API":
            node["position"] = [600, 300]
            # Reset body parameters
            node["parameters"]["bodyParameters"]["parameters"] = [
                {
                    "name": "job_id",
                    "value": "={{ $json.body.job_id }}"
                },
                {
                    "name": "month",
                    "value": "={{ $json.body.month }}"
                },
                {
                    "name": "year",
                    "value": "={{ $json.body.year }}"
                },
                {
                    "name": "days_in_month",
                    "value": "={{ $json.body.days_in_month }}"
                }
            ]
            
    # Update Connections
    # Connect Webhook directly to Call Flask API
    connections["Webhook (Frontend Trigger)"] = {
        "main": [
            [{"node": "Call Flask API", "type": "main", "index": 0}]
        ]
    }
    
    # Remove old connections
    if "Read CSV" in connections: del connections["Read CSV"]
    if "Extract CSV" in connections: del connections["Extract CSV"]
    if "Aggregate" in connections: del connections["Aggregate"]
    
    with open(workflow_path, "w") as f:
        json.dump(workflow, f, indent=2)
        
    print("Workflow updated for monthly scheduling.")

if __name__ == "__main__":
    update_workflow()
