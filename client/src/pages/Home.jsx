import ActivityCard from "../components/ActivityCard";

const ACTIVITIES = [
  {
    key: "brain_buster",
    emoji: "🧩",
    title: "Brain Buster",
    description: "Solve fun riddles! Ask for hints if you're stuck.",
    accent: "brain-buster",
  },
  {
    key: "quick_fire",
    emoji: "⚡",
    title: "Quick Fire",
    description: "Answer quick trivia questions about science, space, animals, and more!",
    accent: "quick-fire",
  },
  {
    key: "ask_explore",
    emoji: "🔭",
    title: "Ask & Explore",
    description: "Curious about something? Ask me anything and let's find out together!",
    accent: "ask-explore",
  },
];

function Home({ onSelectActivity }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-12">
      <div className="text-center mb-10">
        <h1 className="text-3xl sm:text-4xl font-extrabold text-ink mb-2">
          🌟 Welcome, Explorer! 🌟
        </h1>
        <p className="text-ink-soft text-base sm:text-lg">
          Pick an activity below to start learning and having fun!
        </p>
      </div>

      <div className="flex flex-col sm:flex-row gap-5 items-center sm:items-stretch">
        {ACTIVITIES.map((a) => (
          <ActivityCard
            key={a.key}
            emoji={a.emoji}
            title={a.title}
            description={a.description}
            accent={a.accent}
            onClick={() => onSelectActivity(a.key)}
          />
        ))}
      </div>

      <p className="text-ink-faint text-xs mt-10 text-center max-w-md">
        Each activity is its own private session. If you're inactive for a
        minute, or head back home, that session ends automatically.
      </p>
    </div>
  );
}

export default Home;
