function ActivityCard({ emoji, title, description, accent, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="activity-card w-full sm:w-64 bg-surface border-2 rounded-3xl p-6 text-left shadow-sm transition-all duration-150"
      style={{ borderColor: `var(--color-${accent})` }}
    >
      <div
        className="w-14 h-14 rounded-2xl flex items-center justify-center text-3xl mb-4"
        style={{ backgroundColor: `var(--color-${accent}-soft)` }}
      >
        {emoji}
      </div>
      <h3 className="text-lg font-bold text-ink mb-1.5">{title}</h3>
      <p className="text-sm text-ink-soft leading-relaxed">{description}</p>
    </button>
  );
}

export default ActivityCard;
