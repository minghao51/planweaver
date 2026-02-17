import { useState } from 'react';
import { Header } from './components/Header';
import { NewPlanForm } from './components/NewPlanForm';
import { PlanView } from './components/PlanView';

type View = 'home' | { type: 'plan'; sessionId: string };

function App() {
  const [view, setView] = useState<View>('home');

  function handlePlanCreated(sessionId: string) {
    setView({ type: 'plan', sessionId });
  }

  return (
    <div style={styles.app}>
      <Header />
      <main style={styles.main}>
        {view === 'home' && (
          <NewPlanForm onPlanCreated={handlePlanCreated} />
        )}
        {view !== 'home' && 'sessionId' in view && (
          <PlanView sessionId={view.sessionId} />
        )}
      </main>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  app: {
    minHeight: '100vh',
    backgroundColor: '#0d0d1a',
  },
  main: {
    paddingBottom: '60px',
  },
};

export default App;
