import ReactMarkdown from "react-markdown";

/** Renders one message bubble. childAccent picks the current activity's color for the avatar. */
function ChatMessage({ role, content, isError = false, childAccent = "brain-buster" }) {
  const isUser = role === "user";
  const shouldRenderMarkdown = !isUser && !isError;

  return (
    <div className={`flex w-full ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div className={`flex items-end gap-2 max-w-[85%] ${isUser ? "flex-row-reverse" : "flex-row"}`}>
        <div
          className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-lg font-semibold text-white ${isUser ? "bg-header" : isError ? "bg-red-400" : `bg-${childAccent}`}`}
          style={!isUser && !isError ? { backgroundColor: `var(--color-${childAccent})` } : undefined}
          aria-hidden="true"
        >
          {isUser ? "🧑" : isError ? "!" : "🤖"}
        </div>

        <div
          className={`rounded-2xl px-4 py-2.5 text-[15px] leading-relaxed break-words shadow-sm ${
            isUser
              ? "bg-header text-header-ink rounded-br-sm whitespace-pre-wrap"
              : isError
              ? "bg-red-50 text-red-700 border border-red-200 rounded-bl-sm whitespace-pre-wrap"
              : "bg-surface text-ink rounded-bl-sm border border-border"
          }`}
        >
          {shouldRenderMarkdown ? (
            <ReactMarkdown>{content}</ReactMarkdown>
          ) : (
            content
          )}
        </div>
      </div>
    </div>
  );
}

export default ChatMessage;