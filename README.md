# Day 14 - Week 2 Review: Full-Stack Kids Educational Chatbot

A complete AI-powered educational web application for children, built
with React and FastAPI, integrating everything from Week 2: streaming
responses, session management, prompt engineering, and performance
monitoring. Three activities -- Brain Buster (riddles), Quick Fire
(trivia), and Ask & Explore (open Q&A) -- each with their own dedicated
system prompt, isolated in-memory session, and a strict 60-second
inactivity timeout enforced both client- and server-side.

**Note on provider:** this project uses Google's Gemini API (free tier)
via its OpenAI-compatible endpoint, using the same `openai` Python SDK
Requirement 9 specifies -- the exact same code also runs unmodified
against a real OpenAI key if `OPENAI_API_KEY` is set instead.

## Project Structure

```
kids-edu-chatbot-day14/
  README.md
  start.sh                 <- one-command startup (Requirement 9)
  notes/
    01_architecture_and_design.md   <- key design decisions, explained
    02_real_bug_found_and_fixed.md  <- a real StrictMode bug, found live
  screenshots/               <- real captured UI states
  server/
    .env.example
    requirements.txt
    app/
      main.py                 <- FastAPI app, 4 endpoints, activity state machine
      content_bank.py          <- 12 riddles + 21 trivia questions (7 topics)
      prompts.py                <- 3 activity system prompts + shared safety preamble
      session_store.py          <- in-memory sessions, dual-layer 60s timeout
      llm_client.py              <- streaming, TTFT + token capture
      monitoring.py               <- dedicated JSON log file (Requirement 8)
      schemas.py                   <- Pydantic request/response models
    logs/
      monitoring.log                <- created at runtime
  client/
    .env.example
    src/
      App.jsx                  <- Home <-> ActivityChat router
      api.js                     <- streaming fetch wrapper
      useInactivityTimer.js       <- 60s client-side timeout hook
      pages/
        Home.jsx                    <- 3 activity cards
        ActivityChat.jsx             <- shared chat UI for all 3 activities
      components/
        ActivityCard.jsx
        ChatMessage.jsx (Markdown-rendered assistant replies)
        MessageInput.jsx (+ Hint/Give Up buttons for Brain Buster)
        TypingIndicator.jsx
```

## Functional Requirements Covered

1. **Home Screen** - `Home.jsx` shows 3 activity cards; selecting one
   opens `ActivityChat.jsx` with a Back button.
2. **Session Management** - each activity creates an independent
   in-memory session (`POST /api/session/start`). 60 seconds of
   inactivity OR clicking Back terminates the session and clears its
   data, enforced on BOTH the client (`useInactivityTimer.js`) and the
   server (a background sweep task, independent of client behavior).
3. **Brain Buster** - one riddle at a time, no repeats within a session,
   up to 3 hints, answer revealed after hint 3 or on give-up, correct/
   incorrect feedback with appropriate next steps.
4. **Quick Fire** - one question at a time across 7 topics, no repeats,
   correct answers get praise + a fact, incorrect answers reveal the
   correct answer with encouragement.
5. **Ask & Explore** - open-ended, simple, age-appropriate Q&A.
6. **AI Safety** - each activity has its own system prompt, all built on
   a shared safety preamble enforcing consistent behavior around abusive
   input, harmful content, and unsafe topics.
7. **Conversation & Response Handling** - only the 6 most recent messages
   are kept as context; every reply streams token-by-token via SSE.
8. **Monitoring** - every LLM request logs timestamp, session_id,
   activity, user prompt, input/output/total tokens, TTFT, and total
   response time to `server/logs/monitoring.log`.
9. **Technical Requirements** - React + FastAPI + the OpenAI SDK
   (pointed at Gemini's free tier), in-memory session storage (no
   database), `.env` configuration, and `start.sh` for one-command setup.

## How to Run

### First-time setup

```bash
cd kids-edu-chatbot-day14/server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and add your GEMINI_API_KEY (free from https://aistudio.google.com/apikey)

cd ../client
npm install
```

### Every time after that

From the project root:
```bash
./start.sh
```

This starts the backend on `http://127.0.0.1:8000` and the frontend on
`http://127.0.0.1:5173` together, and stops the backend automatically
when you press Ctrl+C.

Or run them separately in two terminals if you prefer:
```bash
# Terminal 1
cd server && source venv/bin/activate && export GEMINI_API_KEY="..." && uvicorn app.main:app --reload

# Terminal 2
cd client && npm run dev
```

Then open **http://127.0.0.1:5173/** in a browser.

## Real Verified Results

Every core mechanic was tested directly, not just written and assumed
correct:

- **Content bank**: 12 riddles, 21 trivia questions across all 7 required
  topics, confirmed via direct inspection. Lenient answer matching
  verified (`"an egg"` vs `"EGG!"` both correctly match `"egg"`).
- **Brain Buster state machine**: a full live-code walkthrough confirmed
  new riddle -> wrong answer -> hint -> correct answer -> next riddle,
  with `used_riddle_indices` growing correctly at each step.
- **3-hint exhaustion**: confirmed the answer is revealed and the session
  automatically advances to a new riddle, with `hints_given` reset to 0.
- **Give-up flow**: confirmed the answer reveals immediately and advances
  to a new riddle, regardless of hint count.
- **Quick Fire**: confirmed correct answers trigger the educational fact
  before advancing, and the question index changes accordingly.
- **All error paths**: verified live via curl -- empty message on
  `action="answer"` -> 400; unknown session -> 404; chat after
  termination -> 404 (session correctly wiped, not just marked inactive).
- **Live session timeout**: with the timeout and sweep interval set to a
  few seconds via environment variables, a real session was created, real
  wall-clock time was allowed to pass, and the session was confirmed
  automatically removed by the background sweep -- proof the 60-second
  guarantee is real and server-enforced, not just a frontend nicety.
- **A real bug found and fixed live**: React StrictMode's double effect
  invocation caused 2 sessions to be created per activity open and 1 to
  be orphaned after clicking Back. Fixed with a `useRef` guard; re-tested
  and confirmed exactly 1 session while active and 0 after Back. Full
  writeup in `notes/02_real_bug_found_and_fixed.md`.
- **Visual verification**: the home screen and an opened activity were
  screenshotted via a headless browser driving the real running app --
  see `screenshots/`.

## Learning Outcomes

- Can design a hybrid architecture where deterministic game logic
  (content selection, no-repeat tracking, correctness grading) lives in
  code while natural-language delivery is genuinely LLM-generated and
  streamed -- and can explain why a 6-message context cap makes this
  split necessary, not just a stylistic choice.
- Can implement a dual-layer inactivity timeout (client timer + an
  independent server-side background sweep) and explain why the
  server-side half is the actual guarantee, not the client's.
- Can build activity-specific system prompts sharing a common,
  consistently-enforced safety baseline.
- Can implement Time to First Token measurement distinct from total
  response time, and capture real token usage on a streamed response via
  provider-supported stream options.
- Can build a dedicated monitoring log, separate from general application
  logs, containing every field a real production system would need to
  analyze LLM request performance.
- Gained real, practical experience diagnosing a live session-leak bug
  down to its exact root cause (an async effect's cleanup closure
  capturing a stale value under StrictMode's double-invocation) and
  fixing it with a minimal, targeted guard.

## Push This Project to GitHub (Linux steps)

```bash
cat > .gitignore << 'GITIGNORE_EOF'
server/venv/
server/__pycache__/
server/logs/*.log
server/.env
client/node_modules/
client/dist/
GITIGNORE_EOF

git init
git config user.name "Ruqqaya Bibi"
git config user.email "ruqqayabibi157@gmail.com"
git add .
git commit -m "Day 14: Full-stack kids educational chatbot (Week 2 capstone)"
git branch -M main
git remote add origin https://github.com/ruqqaya184/kids-edu-chatbot-day14.git
git push -u origin main
```

**Important:** never commit your `OPENAI_API_KEY`, `GEMINI_API_KEY`, or
any real API key to GitHub. Keep them in `server/.env` (already excluded
by the `.gitignore` above).

## Author

Ruqqaya Bibi
