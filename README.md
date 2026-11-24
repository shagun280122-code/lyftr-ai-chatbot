# Lyftr AI Chatbot

## Project Overview

Lyftr AI is an AI-powered chatbot application developed to provide users with an interactive conversational experience. It uses a React-based frontend and a FastAPI backend integrated with LiteLLM to generate AI-powered responses.

The application supports session-based conversations and stores chat messages using an SQLite database.

## Features

- Interactive and user-friendly chatbot interface.
- AI-generated responses through LiteLLM.
- Multi-turn conversations using unique session IDs.
- Chat history storage using SQLite.
- REST API integration using FastAPI.
- API key management through environment variables.
- Response caching to improve efficiency.
- Provider fallback support for improved reliability.
- Backend health-check endpoint.

## Technology Stack

| Component | Technologies |
|---|---|
| Frontend | React, Vite, JavaScript, CSS |
| Backend | Python, FastAPI |
| AI Integration | LiteLLM, Google Gemini |
| Database | SQLite |
| API Communication | REST API |
| Development Tools | VS Code, Git, GitHub |

## Project Structure

```text
lyftr-ai-chatbot/
│
├── backend/
│   ├── main.py
│   ├── database.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   ├── public/
│   ├── package.json
│   └── package-lock.json
│
├── .gitignore
└── README.md
```

## Installation and Setup

### Prerequisites

- Python 3.10 or later
- Node.js and npm
- Git
- A valid Google Gemini API key

### 1. Clone the Repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd lyftr-ai-chatbot
```

### 2. Backend Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the required dependencies:

```bash
pip install -r backend/requirements.txt
```

Create a `.env` file in the root directory and configure the following variables:

```env
LLM_MODEL=gemini/gemini-flash-lite-latest
LLM_API_KEYS=your_api_key_here
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Replace the placeholder with your own API key. Never upload your actual `.env` file to GitHub.

Start the backend server:

```bash
python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
```

### 3. Frontend Setup

Open a separate terminal and navigate to the frontend directory:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL displayed in the terminal to access Lyftr AI.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Checks backend health and configuration status |
| POST | `/chat` | Sends a message and receives an AI-generated response |
| GET | `/sessions/{session_id}/messages` | Retrieves conversation history for a session |

## Future Enhancements

- Improved chatbot personalization.
- Enhanced conversation management.
- Additional AI model integrations.
- Further improvements to the user interface.

## Conclusion

Lyftr AI demonstrates the integration of modern frontend technologies, backend API development, database management, and large language models to build an interactive AI chatbot application.

**Developed as an academic project.**
