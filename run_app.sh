#!/bin/bash

# 1. Setup Backend (Python)
echo "--- Setting up Python Backend ---"
cd backend || exit
python3 -m venv venv
source venv/bin/activate

echo "Installing Python dependencies..."
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "No requirements.txt found, skipping..."
fi

# Run backend in the background
echo "Starting Backend..."
python3 receiver.py & 
BACKEND_PID=$!

# 2. Setup Frontend (Node.js)
echo "--- Setting up Frontend ---"
cd ../frontend || exit

echo "Installing Node dependencies..."
npm install

# Run frontend
echo "Starting Frontend on 0.0.0.0..."
# Using --host to ensure it's accessible from your laptop
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!

echo "---------------------------------------"
echo "Both services are starting up!"
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo "Press Ctrl+C to stop both."
echo "---------------------------------------"

# Wait for user to exit
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait