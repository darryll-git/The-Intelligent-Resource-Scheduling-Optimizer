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
llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)

def analyze_query(state: AgentState):
    """Analyzes the user's query to determine what aspect of the schedule they are asking about."""
    messages = state["messages"]
    last_message = messages[-1].content
    
    prompt = f"Analyze this user query about a schedule and determine the core intent (e.g., questioning fairness, back-to-back shifts, or asking about a specific person). Query: {last_message}"
    
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"query_intent": response.content}

def retrieve_constraints(state: AgentState):
    """Retrieves schedule data and solver logs to provide context for the reasoning."""
    context = ""
    if LOCAL_MODE:
        base_dir = os.path.dirname(__file__)
        schedule_path = os.path.join(base_dir, "schedule_output.json")
        staff_path = os.path.join(base_dir, "staff_data.json")
        
        schedule_data = []
        staff_data = []
        
        if os.path.exists(schedule_path):
            with open(schedule_path, "r", encoding="utf-8") as f:
                schedule_data = json.load(f)
        if os.path.exists(staff_path):
            with open(staff_path, "r", encoding="utf-8") as f:
                staff_data = json.load(f)
                
        # Only take a snippet if it's too large, but for constraints logic, full data is better.
        context = f"Local Schedule Data: {schedule_data}\nStaff Data: {staff_data}"
    else:
        try:
            shifts = supabase.table("fact_shifts").select("*").limit(50).execute().data
            logs = supabase.table("solver_logs").select("*").order("created_at", desc=True).limit(5).execute().data
            staff = supabase.table("dim_staff").select("*").execute().data
            context = f"Recent Shifts: {shifts}\nRecent Solver Logs: {logs}\nStaff Data: {staff}"
        except Exception as e:
            context = f"Failed to retrieve data from Supabase: {e}"
            
    return {"constraints_context": context}

def evaluate_logic(state: AgentState):
    """Evaluates the mathematical/logical constraints that forced a decision."""
    intent = state.get("query_intent", "")
    context = state.get("constraints_context", "")
    user_query = state["messages"][-1].content
    
    prompt = f"""
    You are an expert operations researcher analyzing an OR-Tools CP-SAT scheduling model. 
    Based on the following schedule constraints, staff limits, and output logs, 
    mathematically explain why the solver made the decisions relevant to the user's query.
    
    User Query: {user_query}
    Query Intent: {intent}
    System Context / Output Logs: 
    {context}
    
    Explain the CP-SAT constraint logic (e.g., boolean implications for back-to-back penalties, 
    integer boundaries for max shifts per week, or variables minimizing variance for fairness). 
    Identify specifically which mathematical constraint or penalty forced this outcome.
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
