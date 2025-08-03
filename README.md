# AI Interviewer

This project is a sophisticated AI-powered platform designed to help users practice for technical interviews. It leverages a modern web stack to deliver a realistic and interactive interview experience, complete with a virtual avatar, real-time feedback, and personalized question generation.

## Key Features

- **Dynamic Question Generation**: The application uses a Large Language Model (LLM) to generate a unique set of interview questions based on the user's chosen domain and difficulty level.
- **Retrieval-Augmented Generation (RAG)**: To ensure the relevance and quality of the interview questions, the application employs a RAG service. This service enhances the LLM's prompts with domain-specific context, resulting in more targeted and realistic questions.
- **Real-time Feedback and Scoring**: After each question, the user's answer is evaluated by the LLM, which provides a score, detailed feedback, and suggestions for improvement.
- **Interactive Avatar**: The frontend features a virtual avatar that uses Azure Speech Services to deliver the interview questions in a conversational manner.
- **Speech-to-Text and Text-to-Speech**: The application uses Azure Speech Services to convert the user's spoken answers into text and to synthesize the avatar's voice.

## Technical Architecture

The application is divided into a frontend and a backend, each with its own set of technologies and responsibilities.

### Frontend

The frontend is a modern, responsive web application built with Next.js and TypeScript. It provides a user-friendly interface for setting up and participating in the interview.

- **Next.js**: The frontend is built with Next.js, a React framework that enables server-side rendering and static site generation. This provides a fast and SEO-friendly user experience.
- **React**: The user interface is built with React, a popular JavaScript library for building user interfaces. The use of React allows for a modular and component-based architecture.
- **Tailwind CSS**: The application is styled with Tailwind CSS, a utility-first CSS framework that allows for rapid and consistent styling.
- **Azure Speech Services**: The frontend integrates with Azure Speech Services to provide the text-to-speech functionality for the virtual avatar.

### Backend

The backend is a Python-based API built with FastAPI. It handles the core logic of the application, including user authentication, question generation, and answer evaluation.

- **FastAPI**: The backend API is built with FastAPI, a high-performance web framework for Python. FastAPI's asynchronous nature makes it well-suited for handling the I/O-bound operations of the application, such as making requests to the LLM and other external services.
- **Ollama**: The application uses Ollama to run the LLM locally. This allows for greater control over the model and reduces the reliance on third-party APIs.
- **Retrieval-Augmented Generation (RAG)**: The backend features a RAG service that enhances the LLM's prompts with domain-specific context. This service uses a file-based knowledge base to retrieve relevant information, which is then used to generate more targeted and realistic interview questions.
- **Azure Speech Services**: The backend integrates with Azure Speech Services to provide the speech-to-text functionality for transcribing the user's spoken answers.
- **SQLite**: A lightweight, serverless SQL database engine is used to store interview session data, including user selections, questions asked, and the final results.