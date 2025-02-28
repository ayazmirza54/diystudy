#!/bin/bash

# Start Flask backend
echo "Starting Flask backend..."
cd backend
# Check if python3 is available, otherwise use python
if command -v python3 &> /dev/null; then
  PYTHON_CMD=python3
else
  PYTHON_CMD=python
fi

# Install backend dependencies if needed
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  $PYTHON_CMD -m venv venv
fi

# Activate virtual environment
source venv/bin/activate || source venv/Scripts/activate

# Install dependencies
pip install -r requirements.txt

# Start the Flask server in the background
$PYTHON_CMD app.py &
BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID"

# Wait a bit for the backend to start up
sleep 2

# Start React frontend
echo "Starting React frontend..."
cd ../frontend

# Install frontend dependencies if needed
if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies..."
  npm install
fi

# Start the frontend
npm run dev &
FRONTEND_PID=$!
echo "Frontend started with PID: $FRONTEND_PID"

# Handle shutdown
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT TERM EXIT

# Keep script running
wait