import json
import os

def update_workflow():
    workflow_path = "n8n/orchestrator_workflow.json"
    with open(workflow_path, "r") as f:
        workflow = json.load(f)
        
    nodes = workflow["nodes"]
    connections = workflow["connections"]
    
    csv_path = os.path.abspath("staff_roster.csv").replace("\\", "/")
    
    # New Nodes
    read_node = {
        "parameters": {
            "operation": "read",
            "fileSelector": csv_path
        },
        "name": "Read CSV",
        "type": "n8n-nodes-base.readWriteFile",
        "typeVersion": 1,
        "position": [350, 300]
    }
    
    extract_node = {
        "parameters": {
            "operation": "read",
            "binaryPropertyName": "data",
            "options": {}
        },
        "name": "Extract CSV",
        "type": "n8n-nodes-base.spreadsheetFile",
        "typeVersion": 1,
        "position": [500, 300]
    }
    
    code_node = {
        "parameters": {
            "jsCode": "const staff = $input.all().map(i => i.json);\nconst webhookData = $('Webhook (Frontend Trigger)').first().json.body;\nreturn [{ json: { body: webhookData, staff_data: staff } }];"
        },
        "name": "Aggregate",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [650, 300]
    }
    
    nodes.extend([read_node, extract_node, code_node])
    
    # Update Call Flask API Node
    for node in nodes:
        if node["name"] == "Call Flask API":
            node["position"] = [800, 300]
            # Add staff_data to bodyParameters
            node["parameters"]["bodyParameters"]["parameters"].append({
                "name": "staff_data",
                "value": "={{ $json.staff_data }}"
            })
            
        if node["name"] == "Check Success":
            node["position"] = [1000, 300]
            
        if node["name"].startswith("Supabase: Write"):
            node["position"][0] = 1200
            
    # Update Connections
    # Disconnect Webhook from Call Flask API
    connections["Webhook (Frontend Trigger)"] = {
        "main": [
            [{"node": "Read CSV", "type": "main", "index": 0}]
        ]
    }
    connections["Read CSV"] = {
        "main": [
            [{"node": "Extract CSV", "type": "main", "index": 0}]
        ]
    }
    connections["Extract CSV"] = {
        "main": [
            [{"node": "Aggregate", "type": "main", "index": 0}]
        ]
    }
    connections["Aggregate"] = {
        "main": [
            [{"node": "Call Flask API", "type": "main", "index": 0}]
        ]
    }
    
    with open(workflow_path, "w") as f:
        json.dump(workflow, f, indent=2)
        
    print("Workflow updated successfully.")

if __name__ == "__main__":
    update_workflow()
