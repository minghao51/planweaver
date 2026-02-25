import { Navigate, Route, Routes, useNavigate, useParams } from 'react-router-dom';
import { Header } from './components/Header';
import { HistoryPage } from './components/HistoryPage';
import { NewPlanForm } from './components/NewPlanForm';
import { PlanView } from './components/PlanView';
import { colors } from './styles/ui';

function App() {
  const navigate = useNavigate();

  return (
    <div style={styles.app}>
      <Header />
      <main style={styles.main}>
        <Routes>
          <Route
            path="/"
            element={
              <NewPlanForm
                onPlanCreated={(sessionId) => navigate(`/plans/${sessionId}`)}
              />
            }
          />
          <Route path="/plans/:sessionId" element={<PlanRoute />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

function PlanRoute() {
  const { sessionId } = useParams<{ sessionId: string }>();
  if (!sessionId) {
    return <Navigate to="/" replace />;
  }

  return <PlanView sessionId={sessionId} />;
}

const styles: Record<string, React.CSSProperties> = {
  app: {
    minHeight: '100vh',
    backgroundColor: colors.bg,
  },
  main: {
    paddingBottom: '60px',
  },
};

export default App;
