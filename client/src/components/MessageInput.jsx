import { useState } from "react";

const MAX_LENGTH = 1000;

/**
 * Text input plus Send, and (only for Brain Buster) a Hint and Give Up
 * button -- Requirement 3 is specifically about Brain Buster's hint
 * system, and giving the child real buttons for "hint" / "give up" is
 * both more reliable than parsing free-text intent and more natural for
 * young users than requiring them to type exact phrases.
 */
function MessageInput({ onSend, onHint, onGiveUp, disabled, showHintButtons, accent }) {
  const [draft, setDraft] = useState("");

  const trimmed = draft.trim();
  const canSend = trimmed.length > 0 && trimmed.length <= MAX_LENGTH && !disabled;

  function handleSend() {
    if (!canSend) return;
    onSend(trimmed);
    setDraft("");
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="border-t border-border bg-surface px-4 py-3">
      <div className="max-w-2xl mx-auto">
        {showHintButtons && (
          <div className="flex gap-2 mb-2">
            <button
              type="button"
              onClick={onHint}
              disabled={disabled}
              className="text-sm font-medium px-3 py-1.5 rounded-full border border-border hover:bg-paper transition-colors disabled:opacity-40"
            >
              💡 Hint
            </button>
            <button
              type="button"
              onClick={onGiveUp}
              disabled={disabled}
              className="text-sm font-medium px-3 py-1.5 rounded-full border border-border hover:bg-paper transition-colors disabled:opacity-40"
            >
              🏳️ Give Up
            </button>
          </div>
        )}
        <div className="flex items-end gap-2">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder="Type your answer here..."
            rows={1}
            className="flex-1 resize-none rounded-xl border border-border bg-paper px-4 py-2.5 text-[15px]
              text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 disabled:opacity-60 disabled:cursor-not-allowed"
            style={{ maxHeight: "120px", overflowY: "auto", "--tw-ring-color": `var(--color-${accent})` }}
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={!canSend}
            className="flex-shrink-0 rounded-xl text-white px-5 py-2.5 text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            style={{ backgroundColor: `var(--color-${accent})` }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

export default MessageInput;
