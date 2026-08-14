function TypingIndicator({ childAccent = "brain-buster" }) {
  return (
    <div className="flex w-full justify-start mb-3">
      <div className="flex items-end gap-2 max-w-[85%]">
        <div
          className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm text-white"
          style={{ backgroundColor: `var(--color-${childAccent})` }}
        >
          🤖
        </div>
        <div className="bg-surface border border-border rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-ink-faint typing-dot" style={{ animationDelay: "0ms" }} />
          <span className="w-2 h-2 rounded-full bg-ink-faint typing-dot" style={{ animationDelay: "150ms" }} />
          <span className="w-2 h-2 rounded-full bg-ink-faint typing-dot" style={{ animationDelay: "300ms" }} />
        </div>
      </div>
    </div>
  );
}

export default TypingIndicator;
