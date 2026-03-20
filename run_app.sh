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

# Ensure backend TLS certificate exists (used by backend/wserver.py)
if [ ! -f "cert.pem" ] || [ ! -f "key.pem" ]; then
    echo "HTTPS certificate not found. Generating self-signed certificate..."
    openssl req -x509 -newkey rsa:4096 -sha256 -days 365 -nodes \
        -keyout key.pem \
        -out cert.pem \
        -subj "/CN=localhost"
else
    echo "Existing HTTPS certificate found (cert.pem/key.pem)."
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