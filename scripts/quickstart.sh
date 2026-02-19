#!/bin/bash

# AI Interviewer - Quick Start Script
# This script sets up everything needed for development

set -e  # Exit on any error

echo "🚀 AI Interviewer - Quick Start"
echo "==============================="

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Please run this script from the ai-interviewer project root directory"
    exit 1
fi

echo "📍 Current directory: $(pwd)"

# Step 1: Initialize project
echo ""
echo "📦 Step 1: Initializing project..."
python3 scripts/init.py

# Step 2: Install dependencies (for IDE support)
echo ""
echo "📦 Step 2: Installing frontend dependencies..."
cd frontend && npm install && cd ..

echo ""
echo "📦 Building backend..."
cd backend && ./mvnw dependency:resolve -B && cd ..

# Step 3: Start development environment
echo ""
echo "🚀 Step 3: Starting development environment..."
echo "This will:"
echo "  - Start backend API server (http://localhost:8000)"
echo "  - Start frontend dev server (http://localhost:3000)" 
echo "  - Start Ollama LLM server (http://localhost:11434)"
echo "  - Download Llama 3.2 model (~4GB, may take a while on first run)"
echo ""

read -p "Continue? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    make dev
    
    echo ""
    echo "🎉 Development environment started!"
    echo ""
    echo "📍 Access points:"
    echo "  • Frontend:    http://localhost:3000"
    echo "  • Backend API: http://localhost:8000"
    echo "  • API Docs:    http://localhost:8000/docs"
    echo "  • Ollama:      http://localhost:11434"
    echo ""
    echo "🔧 Useful commands:"
    echo "  • make logs    - View container logs"
    echo "  • make clean   - Stop and clean up"
    echo "  • make help    - Show all commands"
    echo ""
    echo "💡 Tip: The first run will download the Ollama model."
    echo "    Check logs with 'make logs' if needed."
else
    echo "Setup cancelled. You can start development later with 'make dev'"
fi
