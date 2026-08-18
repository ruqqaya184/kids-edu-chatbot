import { useEffect, useRef, useState } from "react";
import ChatMessage from "../components/ChatMessage";
import MessageInput from "../components/MessageInput";
import TypingIndicator from "../components/TypingIndicator";
import { startSession, endSession, streamActivityTurn } from "../api";
import { useInactivityTimer } from "../useInactivityTimer";

const ACTIVITY_META = {
  brain_buster: { title: "🧩 Brain Buster", accent: "brain-buster", showHints: true },
  quick_fire: { title: "⚡ Quick Fire", accent: "quick-fire", showHints: false },
  ask_explore: { title: "🔭 Ask & Explore", accent: "ask-explore", showHints: false },
};

function ActivityChat({ activity, onBack }) {
  const meta = ACTIVITY_META[activity];
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const scrollRef = useRef(null);
  const sessionIdRef = useRef(null); // avoids stale closures in the timeout/unmount handlers

  function handleTimeout() {
    // Requirement 2: 60s of inactivity terminates the session and returns
    // to the home screen, with no session data left behind.
    if (sessionIdRef.current) endSession(sessionIdRef.current);
    onBack();
  }

  const { resetActivity, showWarning } = useInactivityTimer(handleTimeout);

  function updateLastMessage(updaterFn) {
    setMessages((prev) => {
      if (prev.length === 0) return prev;
      const copy = [...prev];
      copy[copy.length - 1] = updaterFn(copy[copy.length - 1]);
      return copy;
    });
  }

    async function runTurn(message) {
    setIsSending(true);
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);
    try {
      await streamActivityTurn(sessionId, message, (deltaText) => {
        updateLastMessage((m) => ({ ...m, content: m.content + deltaText }));
      });
    } catch (err) {
      updateLastMessage(() => ({ role: "assistant", content: `Oops! Something went wrong: ${err.message}`, isError: true }));
    } finally {
      setIsSending(false);
    }
  }

  // Start a fresh session the moment this activity opens, and immediately
  // trigger the first turn (the first riddle/question, or a greeting for
  // Ask & Explore).
  //
  // The hasStarted ref guard is necessary because React's StrictMode
  // (enabled by default in development) intentionally double-invokes
  // effects on mount to help surface bugs like this one -- without it,
  // TWO sessions get created per activity open, and because the second
  // effect run's cleanup captures a different session_id in its closure
  // than the one actually left active, the Back button was found (via
  // live testing) to leave one orphaned session behind on the server
  // instead of cleanly terminating it. Verified after the fix: exactly
  // one session while inside an activity, and zero after clicking Back.
  const hasStarted = useRef(false);
  useEffect(() => {
    if (hasStarted.current) return;
    hasStarted.current = true;

    (async () => {
      try {
        const result = await startSession(activity);
        setSessionId(result.session_id);
        sessionIdRef.current = result.session_id;
      } catch (err) {
        setMessages([{ role: "assistant", content: `Could not start this activity: ${err.message}`, isError: true }]);
      }
    })();

    return () => {
      if (sessionIdRef.current) endSession(sessionIdRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activity]);

     const hasSentFirstTurn = useRef(false);
  useEffect(() => {
    if (!sessionId) return;
    if (hasSentFirstTurn.current) return;
    hasSentFirstTurn.current = true;
    runTurn(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, isSending]);

   function handleSend(text) {
    resetActivity();
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    runTurn(text);
  }
    function handleHint() {
    resetActivity();
    const text = "Can I get a hint?";
    setMessages((prev) => [...prev, { role: "user", content: "💡 " + text }]);
    runTurn(text);
  }

  function handleGiveUp() {
    resetActivity();
    const text = "I give up, what's the answer?";
    setMessages((prev) => [...prev, { role: "user", content: "🏳️ " + text }]);
    runTurn(text);
  }
  function handleBackClick() {
    if (sessionIdRef.current) endSession(sessionIdRef.current);
    onBack();
  }

  const lastMessage = messages[messages.length - 1];
  const showTrailingIndicator = isSending && (!lastMessage || lastMessage.content.length === 0);

  return (
    <div className="h-screen flex flex-col bg-paper">
      <header
        className="sticky top-0 z-10 text-white px-4 py-3.5 flex items-center justify-between shadow-md"
        style={{ backgroundColor: `var(--color-${meta.accent})` }}
      >
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleBackClick}
            className="text-sm font-medium bg-white/20 hover:bg-white/30 rounded-full px-3 py-1.5 transition-colors"
          >
            ← Back
          </button>
          <h1 className="text-[16px] font-bold">{meta.title}</h1>
        </div>
        {showWarning && (
          <div className="text-xs bg-white/20 rounded-full px-3 py-1.5 font-medium animate-pulse">
            Still there? Session ending soon...
          </div>
        )}
      </header>

      <main ref={scrollRef} className="flex-1 overflow-y-auto chat-scroll px-4 py-6">
        <div className="max-w-2xl mx-auto">
          {messages.map((m, i) => (
            <ChatMessage key={i} role={m.role} content={m.content} isError={m.isError} childAccent={meta.accent} />
          ))}
          {showTrailingIndicator && <TypingIndicator childAccent={meta.accent} />}
        </div>
      </main>

      <MessageInput
        onSend={handleSend}
        onHint={handleHint}
        onGiveUp={handleGiveUp}
        disabled={isSending || !sessionId}
        showHintButtons={meta.showHints}
        accent={meta.accent}
      />
    </div>
  );
}

export default ActivityChat;
