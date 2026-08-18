/**
 * api.js
 * ========
 *
 * All network calls to the FastAPI backend: starting/ending a session,
 * and streaming an activity turn (chat) token-by-token via Server-Sent
 * Events. Follows the same streaming-consumption pattern established in
 * earlier weeks: raw ReadableStream reading (not EventSource, which
 * cannot POST).
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function postJson(path, payload) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (networkError) {
    throw new Error(`Could not reach the server at ${API_BASE_URL}. Is the backend running? (${networkError.message})`);
  }

  let body;
  try {
    body = await response.json();
  } catch {
    throw new Error(`The server responded with status ${response.status}, but the body was not valid JSON.`);
  }

  if (!response.ok) {
    throw new Error(body.detail || body.error || `Request failed with status ${response.status}`);
  }
  return body;
}

/** Starts a brand-new, independent session for one activity. Returns { session_id, activity }. */
export async function startSession(activity) {
  return postJson("/api/session/start", { activity });
}

/** Immediately terminates a session server-side (best-effort -- the server also enforces this via its own inactivity sweep regardless). */
export async function endSession(sessionId) {
  try {
    await fetch(`${API_BASE_URL}/api/session/${sessionId}`, { method: "DELETE" });
  } catch {
    // Best-effort: if this fails (e.g. the tab is closing), the server's
    // own background sweep will still clean up the session within 60s.
  }
}

/**
 * Streams one activity turn. message is whatever plain-text message the
 * child is sending this turn -- typed input, or the text a UI button
 * (Hint / Give Up) sends on the child's behalf (e.g. "Can I get a
 * hint?"). There is no more "action" concept: the LLM itself determines
 * what kind of message it received, guided by the system prompt.
 * Calls onDelta(text) per chunk as it streams in.
 */
export async function streamActivityTurn(sessionId, message, onDelta) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
    });
  } catch (networkError) {
    throw new Error(`Could not reach the server at ${API_BASE_URL}. Is the backend running? (${networkError.message})`);
  }

  if (!response.ok) {
    let body;
    try {
      body = await response.json();
    } catch {
      throw new Error(`Request failed with status ${response.status}`);
    }
    throw new Error(body.detail || body.error || `Request failed with status ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let sawDone = false;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop();

    for (const frame of frames) {
      if (!frame.startsWith("data: ")) continue;
      const payload = JSON.parse(frame.slice(6));

      if (payload.type === "delta") {
        onDelta(payload.text);
      } else if (payload.type === "error") {
        throw new Error(payload.detail);
      } else if (payload.type === "done") {
        sawDone = true;
      }
    }
  }

  if (!sawDone) {
    throw new Error("Stream ended unexpectedly without a completion signal.");
  }
}
