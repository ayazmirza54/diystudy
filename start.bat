@echo off
echo Starting application...

rem Start backend
start cmd /k "cd backend && python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt && python app.py"

rem Wait a bit for the backend to initialize
timeout /t 5

rem Start frontend
start cmd /k "cd frontend && npm install && npm run dev"

echo Both services are starting. Check the opened command windows for details.
echo Press any key to shut down both services...
pause > nul

rem Find and kill the processes
taskkill /f /im node.exe > nul 2>&1
taskkill /f /im python.exe > nul 2>&1

echo Services shut down.