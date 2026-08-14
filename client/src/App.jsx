import { useState } from "react";
import Home from "./pages/Home";
import ActivityChat from "./pages/ActivityChat";

function App() {
  const [activeActivity, setActiveActivity] = useState(null);

  if (activeActivity) {
    return <ActivityChat activity={activeActivity} onBack={() => setActiveActivity(null)} />;
  }

  return <Home onSelectActivity={setActiveActivity} />;
}

export default App;
