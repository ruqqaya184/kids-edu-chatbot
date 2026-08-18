# Kids Educational Chatbot

A full-stack, kid-friendly educational chatbot with three interactive learning activities: **Brain Buster**, **Quick Fire**, and **Ask & Explore**. Built as a Day 14 capstone project.

## Features

- **Brain Buster** — Solve riddles with optional hints, powered by an LLM that generates fresh riddles and evaluates answers conversationally.
- **Quick Fire** — Answer rapid trivia questions across topics like science, space, animals, and geography, with encouraging feedback on every answer.
- **Ask & Explore** — Open-ended Q&A where kids can ask about anything and get clear, age-appropriate explanations.
- Independent, isolated sessions per activity with automatic session expiry after a period of inactivity.
- Real-time streaming responses (token-by-token) for a natural, conversational feel.

## Tech Stack

**Backend**
- FastAPI (Python)
- Uvicorn (ASGI server)
- OpenAI-compatible client, routed to Google Gemini via Gemini's OpenAI-compatible endpoint
- python-dotenv for environment configuration

**Frontend**
- React (Vite)
- Tailwind CSS v4

## Project Structure

kids-edu-chatbot/
- client/ — React frontend
  - src/
    - App.jsx
    - api.js
    - useInactivityTimer.js
    - pages/
      - Home.jsx
      - ActivityChat.jsx
    - components/
      - ActivityCard.jsx
      - ChatMessage.jsx
      - MessageInput.jsx
      - TypingIndicator.jsx
- server/ — FastAPI backend
  - app/
    - main.py
    - content_bank.py
    - prompts.py
    - session_store.py
    - llm_client.py
    - monitoring.py
    - schemas.py

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/api/session/start` | Start a new, independent session for one activity |
| `DELETE` | `/api/session/{session_id}` | Immediately terminate a session and clear its data |
| `POST` | `/api/chat/stream` | Send a message/action and stream the activity's reply token-by-token |

Full interactive API docs available at `/docs` once the backend is running (Swagger UI).

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- A Gemini API key (or an OpenAI API key)

### Backend

Run these commands:

    cd server
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env

On Windows, use `venv\Scripts\activate` instead of `source venv/bin/activate`.

Edit `server/.env` and set **one** of the following:

    GEMINI_API_KEY=your_actual_key_here

or

    OPENAI_API_KEY=your_actual_key_here

Then start the server:

    uvicorn app.main:app --reload

The backend will be available at `http://127.0.0.1:8000`.

### Frontend

In a separate terminal:

    cd client
    npm install
    npm run dev

The frontend will be available at `http://localhost:5173`.

### Usage

1. Open `http://localhost:5173` in your browser.
2. Pick an activity: Brain Buster, Quick Fire, or Ask & Explore.
3. Chat away! Each activity runs as its own private, independent session and will automatically end after a period of inactivity.

## License

This project was built as part of a Day 14 capstone assignment for educational purposes.