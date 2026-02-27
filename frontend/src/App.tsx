import { Navigate, Route, Routes, useNavigate, useParams } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { Header } from './components/Header';
import { HistoryPage } from './components/HistoryPage';
import { NewPlanForm } from './components/NewPlanForm';
import { PlanView } from './components/PlanView';
import { Toast } from './components/Toast';
import { useToast } from './hooks/useToast';

function App() {
  const navigate = useNavigate();
  const { toasts, remove } = useToast();

  return (
    <div className="app-shell min-h-screen bg-bg text-text-body font-sans selection:bg-primary/30">
      <Header />
      <main className="container mx-auto px-4 py-8 sm:px-6 sm:py-10">
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
      <div className="fixed top-4 right-4 z-50 flex flex-col gap-2">
        <AnimatePresence>
          {toasts.map((toast) => (
            <Toast key={toast.id} id={toast.id} message={toast.message} type={toast.type} onClose={remove} />
          ))}
        </AnimatePresence>
      </div>
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
