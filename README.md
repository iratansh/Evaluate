# AI Interviewer

A sophisticated AI-powered platform designed to help users practice for technical interviews with realistic, interactive experiences. The system features a virtual avatar, real-time feedback, speech-to-text capabilities, and personalized question generation across multiple technical domains.

## Features

### Core Functionality

- **AI-Powered Question Generation**: Dynamic interview questions using Ollama LLM with domain-specific context
- **Multi-Domain Support**: Software Engineering, Data Science, AI/ML, Hardware/ECE, and Robotics
- **Speech Integration**: Full speech-to-text and text-to-speech capabilities using Azure Speech Services
- **Interactive Avatar**: Professional animated avatar that speaks questions and provides feedback
- **Real-time Scoring**: Intelligent evaluation with detailed feedback and improvement suggestions
- **Timed Sessions**: Realistic interview timing with automatic session management

### Advanced Features

- **RAG-Enhanced Questions**: Retrieval-Augmented Generation for contextually relevant questions
- **Audio Recording**: High-quality audio capture with WebM/WAV support and automatic conversion
- **Comprehensive Feedback**: Detailed scoring (0-10), feedback analysis, and actionable suggestions
- **Session Management**: Complete interview lifecycle from setup to results
- **Responsive Design**: Modern, mobile-friendly interface built with Next.js and Tailwind CSS
- **Containerized Deployment**: Full Docker support with development and production configurations

## Architecture

### Frontend (Next.js + TypeScript)

- **Framework**: Next.js 14 with TypeScript
- **UI**: Tailwind CSS with custom components
- **Audio**: Custom `useAudioRecorder` hook with WebRTC integration
- **State Management**: React hooks with optimized performance
- **Animation**: Canvas-based avatar with audio visualization

### Backend (FastAPI + Python)

- **API**: FastAPI with async/await patterns
- **Database**: SQLite with SQLAlchemy ORM
- **AI/ML**: Ollama integration for local LLM inference
- **Speech**: Azure Speech Services for STT/TTS
- **Storage**: Local and Azure Blob Storage support
- **Testing**: Comprehensive test suite with pytest

### Infrastructure

- **Containerization**: Docker & Docker Compose
- **CI/CD**: GitHub Actions pipeline
- **Development**: Hot reload for both frontend and backend
- **Production**: Optimized builds with health checks

## Tech Stack

| Component            | Technology                                             |
| -------------------- | ------------------------------------------------------ |
| **Frontend**   | Next.js 14, React 18, TypeScript 5.3, Tailwind CSS 3.4 |
| **Backend**    | FastAPI, Python 3.8+, SQLAlchemy, Pydantic             |
| **AI/ML**      | Ollama (llama3.2), RAG with file-based knowledge base  |
| **Speech**     | Azure Speech Services (STT/TTS)                        |
| **Database**   | SQLite (development), PostgreSQL ready                 |
| **Storage**    | Local filesystem, Azure Blob Storage                   |
| **Testing**    | Pytest, Jest, GitHub Actions                           |
| **Deployment** | Docker, Docker Compose                                 |

## Prerequisites

- **Docker & Docker Compose** (recommended)
- **Python 3.8+** (for manual backend setup)
- **Node.js 18+** (for manual frontend setup)
- **Ollama** (for LLM functionality)
- **Azure Speech Services** (optional, for voice features)

### Environment Variables

#### Backend (.env)

```env
# Database
DATABASE_URL=sqlite:///./ai_interviewer.db

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Azure Speech Services (Optional)
AZURE_SPEECH_KEY=your_speech_key
AZURE_SPEECH_REGION=your_region
AZURE_STORAGE_CONNECTION_STRING=your_storage_connection
```

#### Frontend (.env.local)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Project Structure

```
ai-interviewer/
├── frontend/                  # Next.js frontend application
│   ├── src/
│   │   ├── app/              # App router pages
│   │   ├── components/       # Reusable UI components
│   │   └── lib/              # Utility functions
│   ├── public/               # Static assets
│   └── package.json
├── backend/                   # FastAPI backend application
│   ├── app/
│   │   ├── api/              # API routes
│   │   ├── models/           # Database models & schemas
│   │   ├── services/         # Business logic (LLM, Speech, RAG)
│   │   └── data/             # Knowledge base topics
│   ├── tests/                # Test suite
│   └── requirements.txt
├── .github/workflows/        # CI/CD pipeline
├── docker-compose.yml        # Development environment
├── docker-compose.prod.yml   # Production environment
└── README.md
```

## CI/CD Pipeline

The project includes a comprehensive GitHub Actions pipeline that:

- Runs backend tests with pytest
- Tests API endpoints with live server
- Runs frontend linting and TypeScript checks
- Validates Docker builds for development and production

### Key Endpoints

| Endpoint                                 | Method | Description                     |
| ---------------------------------------- | ------ | ------------------------------- |
| `/api/interview/domains`               | GET    | Get available interview domains |
| `/api/interview/sessions`              | POST   | Create new interview session    |
| `/api/interview/questions`             | POST   | Generate next question          |
| `/api/interview/questions/{id}/answer` | POST   | Submit text answer              |
| `/api/interview/questions/{id}/audio`  | POST   | Submit audio answer             |
| `/api/interview/questions/{id}/speech` | GET    | Get question TTS audio          |
| `/api/interview/feedback/speech`       | POST   | Get feedback TTS audio          |

## Usage

1. **Start Session**: Choose domain (Software Engineering, Data Science, etc.) and difficulty
2. **Answer Questions**: Respond via text input or voice recording
3. **Receive Feedback**: Get real-time scoring and improvement suggestions
4. **Complete Interview**: View comprehensive results and performance analysis

## Interview Domains

- **Software Engineering**: System design, algorithms, data structures, architecture
- **Data Science**: Statistics, machine learning, data analysis, visualization
- **AI/ML**: Neural networks, deep learning, model evaluation, optimization
- **Hardware/ECE**: Circuit design, digital systems, signal processing, embedded systems
- **Robotics**: Control systems, kinematics, sensors, autonomous navigation

## Development

### Adding New Domains

1. Create topic file in `backend/app/data/{domain_name}/topics.md`
2. Update domain list in `backend/app/api/interview.py`
3. Add domain-specific keywords in `backend/app/services/llm.py`

### Customizing the Avatar

Modify the avatar rendering in `frontend/src/app/interview/session/[id]/avatar.tsx`

### Extending Speech Features

Configure additional Azure Speech Services features in `backend/app/services/speech.py`

## Environment-Specific Configurations

- **Development**: Hot reload, debug logging, development APIs
- **Production**: Optimized builds, health checks, security headers--

**Built using modern web technologies for the next generation of interview preparation.**
