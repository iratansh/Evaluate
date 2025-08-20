.PHONY: help setup dev test clean install-deps start-local logs

help:
	@echo "AI Interviewer - Available commands:"
	@echo "  setup         - Initial project setup"
	@echo "  install-deps  - Install all dependencies"
	@echo "  dev           - Start development environment with Docker"
	@echo "  start-local   - Start without Docker (requires local Ollama)"
	@echo "  test          - Run tests"
	@echo "  logs          - Show container logs"
	@echo "  clean         - Clean up development environment"

setup:
	@echo "Setting up AI Interviewer project..."
	@echo "Copying environment files..."
	cp backend/.env.example backend/.env
	@echo "Installing dependencies..."
	$(MAKE) install-deps
	@echo "Setup complete! Run 'make dev' to start with Docker or 'make start-local' for local development"

install-deps:
	@echo "Installing backend dependencies..."
	cd backend && python -m pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

dev:
	@echo "Starting development environment with Docker..."
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
	@echo "Ollama: http://localhost:11434"
	docker-compose up -d
	@echo "Pulling Ollama model (this may take a while on first run)..."
	@sleep 5
	docker-compose exec ollama ollama pull llama3.2 || echo "Ollama model will be pulled when first used"

start-local:
	@echo "Starting local development (requires Ollama installed locally)..."
	@echo "Make sure Ollama is running: 'ollama serve'"
	@echo "And pull the model: 'ollama pull llama3.2'"
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
	cd frontend && npm run dev &
	@echo "Servers started. Backend: http://localhost:8000, Frontend: http://localhost:3000"

logs:
	docker-compose logs -f

test:
	@echo "Running backend tests..."
	cd backend && python -m pytest tests/ -v
	@echo "Running frontend tests..."
	cd frontend && npm run test

clean:
	@echo "Cleaning up development environment..."
	docker-compose down -v
	docker system prune -f
	@echo "Development environment cleaned up"

# Additional commands for Azure deployment
azure-setup:
	@echo "Setting up Azure resources..."
	# TODO: Add Azure CLI commands for resource creation
	
azure-deploy:
	@echo "Deploying to Azure..."
	# TODO: Add deployment scripts