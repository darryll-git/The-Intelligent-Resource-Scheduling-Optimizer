# The Intelligent Resource & Scheduling Optimizer ⚙️🧠

An end-to-end, AI-enhanced scheduling and logistics optimizer. This application ingests raw scheduling requests, transforms the data into an analytical warehouse, computes optimal resource allocations using linear programming, and provides a Retrieval-Augmented Generation (RAG) interface for natural language querying of the generated schedules.

## 📖 Project Overview

Scheduling in complex environments (like clinic staffing or delivery routing) often falls victim to the "Cynefin Complex Domain"—where the right answers aren't obvious until after the fact. This project solves that by utilizing a two-pronged approach:
1. **Deterministic Optimization:** Using Google OR-Tools to solve the hard constraints (e.g., maximum shifts per week, required skills per shift).
2. **Generative AI Interface:** Allowing stakeholders to query the system's reasoning in natural language (e.g., "Why was Dr. Smith assigned to the night shift on Tuesday?").

## 🔄 System Flow & Architecture

The application is structured into five distinct phases, moving from raw data to AI-driven insights:

1. **Business Logic & API Layer (Flask/React):** The entry point where admins or managers input constraints and view the final schedules via a React frontend, powered by a Flask API.
2. **Data Transformation (dbt):** Raw scheduling logs and user availability are transformed using Kimball dimensional modeling into clean `Fact_Shifts` and `Dim_Staff` tables.
3. **The Engine (Google OR-Tools):** A Python-based worker pulls the clean data, formulates the linear programming problem, and generates the mathematically optimal schedule.
4. **The AI Interface (Ollama / Streamlit):** The finalized schedule and the solver's execution logs are embedded into a vector store. A Streamlit RAG pipeline allows users to "chat" with the schedule.
5. **Evaluation & Auditing:** Continuous logging of the solver's decisions and the LLM's outputs to ensure alignment with OECD AI Ethics Principles (fairness, transparency).

## 🗂️ Project Structure

```text
intelligent-scheduler/
├── backend/                 # Flask API & OR-Tools Engine
│   ├── app.py               # Main Flask application entry point
│   ├── engine/              # Google OR-Tools optimization logic
│   │   ├── solver.py        # Core scheduling algorithm
│   │   └── constraints.py   # Business rules definitions
│   ├── routes/              # API endpoints (e.g., /api/schedule)
│   └── requirements.txt     # Backend Python dependencies
├── frontend/                # React User Interface
│   ├── src/
│   │   ├── components/      # React components (Calendar, Staff Forms)
│   │   ├── App.js           # Main React component
│   │   └── index.js         # React DOM rendering
│   ├── package.json         # Node.js dependencies
│   └── public/              # Static assets
├── data_pipeline/           # dbt Transformations
│   ├── models/
│   │   ├── staging/         # Raw data cleaning models
│   │   └── marts/           # Fact & Dimension tables (Kimball architecture)
│   ├── seeds/               # CSV files with static dimension data
│   └── dbt_project.yml      # dbt configuration
├── ai_interface/            # Streamlit & RAG Application
│   ├── app.py               # Streamlit interactive UI entry point
│   ├── rag/                 # Local LLM orchestration
│   │   ├── embedder.py      # Logic for chunking and vectorizing logs
│   │   └── query_engine.py  # Langchain/Ollama interaction logic
│   └── requirements.txt     # AI-specific Python dependencies
└── README.md                # This documentation file