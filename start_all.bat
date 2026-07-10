@echo off
echo =======================================================
echo Starting The Intelligent Resource & Scheduling Optimizer
echo =======================================================

echo.
echo [1/3] Starting Flask Backend (Port 5000)...
start "Flask Backend" cmd /k "python engine\app.py"

echo.
echo [2/3] Starting n8n Orchestrator (Port 5678)...
start "n8n" cmd /k "npx n8n"

echo.
echo [3/3] Starting Next.js Frontend (Port 3000)...
cd frontend
start "Next.js Frontend" cmd /k "npm run dev"
cd ..

echo.
echo All services are booting up in separate windows!
echo - Flask Backend will be on http://localhost:5000
echo - n8n Orchestrator will be on http://localhost:5678
echo - Next.js Frontend will be on http://localhost:3000
echo.
echo NOTE: Since you are using the real n8n, make sure you open http://localhost:5678, import the n8n/orchestrator_workflow.json blueprint, add your Supabase credentials, and set the workflow to 'Active' before generating a schedule!
echo =======================================================
pause
