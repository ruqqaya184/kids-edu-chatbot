# Kids Educational Chatbot

A full-stack, kid-friendly educational chatbot with three interactive learning activities: **Brain Buster**, **Quick Fire**, and **Ask & Explore**. Built as a Day 14 capstone project.

## Features

- **Brain Buster** — Solve riddles with hints, powered by an LLM that invents a brand-new riddle every time and grades the child's answer itself — no fixed riddle list.
- **Quick Fire** — Answer rapid trivia questions across topics like science, mathematics, geography, English, animals, space, and general knowledge, all generated live by the LLM with encouraging, explanatory feedback on every answer.
- **Ask & Explore** — Open-ended Q&A where kids can ask about anything and get clear, age-appropriate explanations.
- Hints and "give up" requests are understood from natural language (e.g. typing "I'm stuck" or "give me a hint" works just as well as clicking a button) — the LLM itself decides how to respond, guided entirely by the system prompt.
- A lightweight per-session state (the currently active riddle/question, plus recently used topics) is tracked server-side and re-injected into the system prompt every turn, giving the LLM reliable memory of its own prior content even though raw conversation history is capped at the 6 most recent messages.
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
    - main.py — routes, session/game-state handling, streaming response logic
    - prompts.py — loads and combines the markdown prompt files below
    - prompts/ — one markdown file per activity, plus shared safety rules
      - common_safety.md — tone and safety rules shared by every activity
      - brain_buster.md
      - quick_fire.md
      - ask_explore.md
    - session_store.py
    - llm_client.py
    - monitoring.py
    - schemas.py

**Note:** `content_bank.py` is no longer used by the running app — it originally held a fixed list of riddles and trivia questions, but riddle/question generation and answer-grading are now handled entirely by the LLM, guided by the prompt files above. The file is kept in the repo as a reference to the earlier design.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/api/session/start` | Start a new, independent session for one activity |
| `DELETE` | `/api/session/{session_id}` | Immediately terminate a session and clear its data |
| `POST` | `/api/chat/stream` | Send a plain-text message and stream the activity's reply token-by-token |

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
3. Chat away! For Brain Buster and Quick Fire, you can type things like "give me a hint" or "I give up" directly instead of using the buttons — the LLM understands either way. Each activity runs as its own private, independent session and will automatically end after a period of inactivity.

## License

This project was built as part of a Day 14 capstone assignment for educational purposes.