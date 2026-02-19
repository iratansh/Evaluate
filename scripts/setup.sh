#!/bin/bash

echo "🚀 AI Interviewer - Setup Script"
echo "================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"

# Create environment file
if [ ! -f "backend/.env" ]; then
    echo "📝 Creating backend/.env from template..."
    cp backend/.env.example backend/.env
    echo "✅ Created backend/.env"
else
    echo "✅ backend/.env already exists"
fi

# Install frontend dependencies (for development)
echo "📦 Installing frontend dependencies..."
cd frontend && npm install
cd ..

# Build backend
echo "📦 Building backend (Java/Spring Boot)..."
cd backend && ./mvnw dependency:resolve -B
cd ..

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Start development environment: make dev"
echo "2. Visit http://localhost:3000 to access the app"
echo "3. Visit http://localhost:8000/docs for API documentation"
echo ""
echo "Note: First run will download Ollama model (~4GB) - this may take a while!"
echo ""
echo "Available commands:"
echo "  make dev        - Start development environment"
echo "  make logs       - View container logs"
echo "  make clean      - Stop and clean up"
echo "  make help       - Show all available commands"
