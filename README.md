# AI Interviewer

An AI-powered platform for practicing technical interviews with realistic, interactive experiences. Features a virtual avatar, real-time feedback, speech-to-text capabilities, and personalized question generation across multiple technical domains.

## Features

- **AI-Powered Question Generation** — Dynamic questions using Ollama LLM with RAG-enhanced, domain-specific context
- **Multi-Domain Support** — Software Engineering, Data Science, AI/ML, Hardware/ECE, and Robotics
- **Speech Integration** — Text-to-speech and speech-to-text via Azure Speech Services
- **Interactive Avatar** — Animated avatar that speaks questions and provides feedback
- **Real-time Scoring** — Intelligent evaluation (0–10) with detailed feedback and improvement suggestions
- **Timed Sessions** — Realistic interview timing with automatic session management
- **Audio Recording** — High-quality audio capture with WebM/WAV support
- **Containerized Deployment** — One-command startup with Docker Compose

## Tech Stack

| Component      | Technology                                                        |
| -------------- | ----------------------------------------------------------------- |
| **Frontend**   | Next.js 14, React 18, TypeScript 5.3, Tailwind CSS 3.4           |
| **Backend**    | Java 17, Spring Boot 3.2, Spring Data JPA, Spring WebFlux        |
| **AI/LLM**    | Ollama (llama3.2), RAG with file-based knowledge base             |
| **Speech**     | Azure Speech Services (STT/TTS)                                  |
| **Database**   | SQLite with Hibernate ORM                                         |
| **Storage**    | Local filesystem, Azure Blob Storage                              |
| **Build**      | Maven 3.9, npm                                                    |
| **Deployment** | Docker, Docker Compose                                            |

## Quick Start

### Prerequisites

- [Docker & Docker Compose](https://docs.docker.com/get-docker/)

### Run with Docker (recommended)

```bash
# Clone the repository
git clone https://github.com/iratansh/Evaluate.git
cd Evaluate

# Start all services (backend, frontend, ollama)
docker compose up --build -d

# Pull the LLM model (first time only, ~2 GB download)
docker compose exec ollama ollama pull llama3.2
```

Once running:

| Service      | URL                          |
| ------------ | ---------------------------- |
| **Frontend** | http://localhost:3000        |
| **Backend**  | http://localhost:8000        |
| **Ollama**   | http://localhost:11434       |

### Run Locally (without Docker)

Requires **Java 17+**, **Node.js 18+**, and [Ollama](https://ollama.com) installed locally.

```bash
# Start Ollama and pull the model
ollama serve &
ollama pull llama3.2

# Start backend
cd backend
./mvnw spring-boot:run

# In a separate terminal — start frontend
cd frontend
npm install
npm run dev
```

### Using Make

```bash
make dev           # Start with Docker Compose
make start-local   # Start without Docker (requires local Ollama)
make test          # Run backend & frontend tests
make logs          # Tail container logs
make clean         # Tear down containers and clean builds
```

## Project Structure

```
Evaluate/
├── backend/                        # Spring Boot backend
│   ├── src/main/java/com/evaluate/aiinterviewer/
│   │   ├── AiInterviewerApplication.java
│   │   ├── config/                 # CORS, Jackson, WebClient config
│   │   ├── controller/             # REST controllers
│   │   ├── dto/                    # Request/response DTOs
│   │   ├── model/                  # JPA entities
│   │   ├── repository/             # Spring Data repositories
│   │   └── service/                # Business logic (LLM, RAG, Speech, Storage)
│   ├── src/main/resources/
│   │   ├── application.properties
│   │   └── data/                   # Domain topic knowledge base (Markdown)
│   ├── src/test/                   # Test suite
│   ├── Dockerfile
│   └── pom.xml
├── frontend/                       # Next.js frontend
│   ├── src/
│   │   ├── app/                    # App router pages
│   │   │   ├── interview/
│   │   │   │   ├── setup/          # Interview configuration page
│   │   │   │   ├── session/[id]/   # Live interview session + avatar
│   │   │   │   └── results/[id]/   # Post-interview results
│   │   ├── components/             # Reusable UI components
│   │   └── lib/                    # Utility functions
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml              # Development environment
├── docker-compose.prod.yml         # Production environment
├── Makefile                        # Convenience commands
└── README.md
```

## API Endpoints

| Endpoint                                    | Method | Description                      |
| ------------------------------------------- | ------ | -------------------------------- |
| `/`                                         | GET    | API status                       |
| `/health/`                                  | GET    | Health check                     |
| `/health/ready`                             | GET    | Readiness check (dependencies)   |
| `/api/interview/domains`                    | GET    | List available interview domains |
| `/api/interview/domains/{domain}/topics`    | GET    | Get topics for a domain          |
| `/api/interview/sessions`                   | POST   | Create a new interview session   |
| `/api/interview/sessions/{id}`              | GET    | Get session details              |
| `/api/interview/sessions/{id}/complete`     | PUT    | Complete an interview session    |
| `/api/interview/sessions/{id}/questions`    | GET    | Get all questions for a session  |
| `/api/interview/questions`                  | POST   | Generate next question           |
| `/api/interview/questions/{id}/answer`      | POST   | Submit a text answer             |
| `/api/interview/questions/{id}/audio`       | POST   | Submit an audio answer           |
| `/api/interview/questions/{id}/speech`      | GET    | Get question TTS audio           |
| `/api/interview/feedback/speech`            | POST   | Get feedback TTS audio           |

## Environment Variables

All variables have sensible defaults for local development. Override as needed:

| Variable                             | Default                      | Description                        |
| ------------------------------------ | ---------------------------- | ---------------------------------- |
| `OLLAMA_BASE_URL`                    | `http://localhost:11434`     | Ollama API endpoint                |
| `OLLAMA_MODEL`                       | `llama3.2`                   | LLM model name                     |
| `SPRING_DATASOURCE_URL`             | `jdbc:sqlite:./ai_interviewer.db` | Database JDBC URL             |
| `AZURE_SPEECH_KEY`                   | *(empty)*                    | Azure Speech Services key          |
| `AZURE_SPEECH_REGION`                | *(empty)*                    | Azure Speech Services region       |
| `AZURE_STORAGE_CONNECTION_STRING`    | *(empty)*                    | Azure Blob Storage connection      |
| `NEXT_PUBLIC_API_URL`                | `http://localhost:8000`      | Backend URL for the frontend       |

## Interview Domains

| Domain                   | Topics                                                          |
| ------------------------ | --------------------------------------------------------------- |
| **Software Engineering** | System design, algorithms, data structures, architecture        |
| **Data Science**         | Statistics, machine learning, data analysis, visualization      |
| **AI/ML**                | Neural networks, deep learning, model evaluation, optimization  |
| **Hardware/ECE**         | Circuit design, digital systems, signal processing, embedded    |
| **Robotics**             | Control systems, kinematics, sensors, autonomous navigation     |

## Development

### Running Tests

```bash
# Backend (Spring Boot)
cd backend && ./mvnw test

# Frontend (Next.js)
cd frontend && npm run test
```

### Adding a New Domain

1. Create a topic file at `backend/src/main/resources/data/{domain_name}/topics.md`
2. The `RagService` auto-discovers domains on startup — no code changes required
3. Optionally add domain-specific keywords in `LlmService.java`

### Customizing the Avatar

Edit the canvas-based avatar in `frontend/src/app/interview/session/[id]/avatar.tsx`

---

**Built with Java, Spring Boot, Next.js, and Ollama for the next generation of interview preparation.**
