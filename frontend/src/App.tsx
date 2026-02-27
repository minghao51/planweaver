import { Navigate, Route, Routes, useNavigate, useParams } from 'react-router-dom';
import { Header } from './components/Header';
import { HistoryPage } from './components/HistoryPage';
import { NewPlanForm } from './components/NewPlanForm';
import { PlanView } from './components/PlanView';

function App() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-bg text-white font-sans selection:bg-primary/30">
      <Header />
      <main className="container mx-auto px-6 py-8">
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

export default App;
