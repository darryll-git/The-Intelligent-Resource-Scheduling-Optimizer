import os
import json
from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

# Optional Supabase import
try:
    from supabase import create_client, Client
except ImportError:
    Client = None

load_dotenv()

# Setup Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

LOCAL_MODE = not (SUPABASE_URL and SUPABASE_KEY)
supabase: Client = None
if not LOCAL_MODE and Client:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Define state for LangGraph
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    query_intent: str
    constraints_context: str
    logic_evaluation: str

# Initialize LLM (Gemini)
# Requires GOOGLE_API_KEY in .env
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)

def analyze_query(state: AgentState):
    """Analyzes the user's query to extract the intent and target entities."""
    messages = state["messages"]
    last_message = messages[-1].content
    
    prompt = f"""
    Analyze the following user query about a schedule. Extract the core intent and any specific entities mentioned.
    Return ONLY a valid JSON object with these keys (use null if not mentioned):
    - "intent": brief description of what they want to know
    - "target_staff_name": name of the staff member
    - "target_shift_type": shift type (e.g., Morning, Night)
    - "target_date": specific date mentioned

    Query: {last_message}
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    
    # Clean the response to ensure it's valid JSON
    content = response.content.replace("```json", "").replace("```", "").strip()
    try:
        parsed_intent = json.loads(content)
        intent_str = json.dumps(parsed_intent)
    except Exception as e:
        intent_str = json.dumps({"intent": content, "target_staff_name": None, "target_shift_type": None, "target_date": None})
        
    return {"query_intent": intent_str}

def retrieve_constraints(state: AgentState):
    """Filters schedule data based on extracted entities and attaches a rule manifest."""
    try:
        query_data = json.loads(state["query_intent"])
    except:
        query_data = {}
        
    target_staff = query_data.get("target_staff_name")
    
    rule_manifest = """
    ACTIVE SOLVER RULES (Rule Manifest):
    1. HARD: Exactly 2 staff members assigned per shift.
    2. HARD: Maximum 1 shift per day per staff member.
    3. HARD: Cannot work a Morning shift immediately following a Night shift.
    4. HARD: Honors maximum shifts per month for each staff member.
    5. HARD: Requires specific skills if defined for a shift type.
    6. HARD: Respects approved unavailability blocks.
    7. SOFT (Objective): Maximizes schedule score based on preference weights vs historical fairness count.
    """

    context = f"{rule_manifest}\n\nFiltered Context:\n"
    
    if LOCAL_MODE:
        base_dir = os.path.dirname(__file__)
        schedule_path = os.path.join(base_dir, "schedule_output.json")
        staff_path = os.path.join(base_dir, "staff_data.json")
        
        if os.path.exists(schedule_path):
            with open(schedule_path, "r", encoding="utf-8") as f:
                schedule_data = json.load(f)
            
            # Filter schedule data if a target staff member was identified
            if target_staff:
                target_staff_lower = target_staff.lower()
                schedule_data = [s for s in schedule_data if target_staff_lower in str(s.get("staff_id", "")).lower()]
                context += f"Shifts involving {target_staff}:\n{json.dumps(schedule_data, indent=2)}\n"
            else:
                context += f"Sample Shifts:\n{json.dumps(schedule_data[:5], indent=2)}... (truncated)\n"
                
        if os.path.exists(staff_path):
            with open(staff_path, "r", encoding="utf-8") as f:
                staff_data = json.load(f)
                
            if target_staff:
                target_staff_lower = target_staff.lower()
                staff_data = [s for s in staff_data if target_staff_lower in s.get("name", "").lower() or target_staff_lower in s.get("staff_id", "").lower()]
                context += f"\nStaff Preferences for {target_staff}:\n{json.dumps(staff_data, indent=2)}\n"
    else:
        try:
            # In a real app we would use SQL filters here based on target_staff
            shifts = supabase.table("fact_shifts").select("*").limit(50).execute().data
            logs = supabase.table("solver_logs").select("*").order("created_at", desc=True).limit(2).execute().data
            context += f"Recent Shifts: {shifts}\nRecent Solver Logs: {logs}\n"
        except Exception as e:
            context += f"Failed to retrieve data from Supabase: {e}"
            
    return {"constraints_context": context}

def evaluate_logic(state: AgentState):
    """Evaluates the mathematical/logical constraints that forced a decision."""
    try:
        intent_data = json.loads(state.get("query_intent", "{}"))
        intent_desc = intent_data.get("intent", "Unknown")
    except:
        intent_desc = state.get("query_intent", "")
        
    context = state.get("constraints_context", "")
    user_query = state["messages"][-1].content
    
    prompt = f"""
    You are an expert operations researcher analyzing an OR-Tools CP-SAT scheduling model. 
    Based on the Rule Manifest and the filtered data context provided, 
    explain why the solver made the decisions relevant to the user query.
    
    User Query: {user_query}
    Query Intent: {intent_desc}
    
    System Context / Output Logs: 
    {context}
    
    Use the explicit rules defined in the Rule Manifest to justify the scheduling decision. 
    Explain which specific rule or combination of rules (e.g. max shifts per day, back-to-back constraints, or preference maximization) led to this outcome for the queried staff member.
    """
    
    response = llm.invoke([SystemMessage(content=prompt)])
    return {"logic_evaluation": response.content}

def generate_response(state: AgentState):
    """Generates the final, user-friendly answer using the evaluated logic."""
    evaluation = state.get("logic_evaluation", "")
    user_query = state["messages"][-1].content
    
    prompt = f"""
    Translate this technical CP-SAT constraint evaluation into a clear, user-friendly explanation.
    
    User Query: {user_query}
    Technical Evaluation: {evaluation}
    
    Provide a final answer that is easy for a manager to understand, while keeping the mathematical justification clear.
    """
    
    response = llm.invoke([SystemMessage(content=prompt)])
    return {"messages": [AIMessage(content=response.content)]}

# Build the graph
workflow = StateGraph(AgentState)

workflow.add_node("analyze_query", analyze_query)
workflow.add_node("retrieve_constraints", retrieve_constraints)
workflow.add_node("evaluate_logic", evaluate_logic)
workflow.add_node("generate_response", generate_response)

workflow.set_entry_point("analyze_query")
workflow.add_edge("analyze_query", "retrieve_constraints")
workflow.add_edge("retrieve_constraints", "evaluate_logic")
workflow.add_edge("evaluate_logic", "generate_response")
workflow.add_edge("generate_response", END)

app = workflow.compile()

def query_agent(question: str):
    """Helper function to run the agent."""
    inputs = {"messages": [HumanMessage(content=question)]}
    result = app.invoke(inputs)
    return result["messages"][-1].content

if __name__ == "__main__":
    print("Welcome to the Intelligent Scheduling AI Assistant (Phase 3 Stateful Agent)!")
    print("Type 'exit' to quit.")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ['exit', 'quit']:
            break
        try:
            response = query_agent(user_input)
            print(f"AI: {response}")
        except Exception as e:
            print(f"Error: {e}. Please ensure GOOGLE_API_KEY is set in your .env file.")
