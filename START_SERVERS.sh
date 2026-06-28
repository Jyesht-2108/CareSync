#!/bin/bash

echo "🚀 Starting CareSync Servers"
echo "=" 

# Kill any existing processes on these ports
echo "Cleaning up existing processes..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null
lsof -ti:5174 | xargs kill -9 2>/dev/null

echo "✅ Ports cleared"
echo ""

# Start backend
echo "🔧 Starting Backend (Port 8000)..."
cd backend
source ../venv/bin/activate 2>/dev/null || source venv/bin/activate 2>/dev/null
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"
cd ..

# Wait a bit for backend to start
sleep 2

# Start frontend
echo ""
echo "🎨 Starting Frontend (Port 5173)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
echo "✅ Frontend started (PID: $FRONTEND_PID)"
cd ..

echo ""
echo "=" 
echo "✅ Both servers started!"
echo ""
echo "🌐 Frontend: http://localhost:5173"
echo "🔌 Backend:  http://localhost:8000"
echo "📊 API Docs: http://localhost:8000/docs"
echo ""
echo "💡 To stop servers:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "Press Ctrl+C to view logs..."
echo "="

# Wait for user interrupt
wait
