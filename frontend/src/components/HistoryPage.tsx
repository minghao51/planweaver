import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { usePlanApi } from '../hooks/useApi';
import { SessionHistoryItem, PlanStatus } from '../types';
import {
  History,
  Search,
  Filter,
  ChevronRight,
  Activity,
  Clock,
  ExternalLink,
  Target
} from 'lucide-react';
import { cn } from '../utils';
import { getStatusStyles } from '../lib/statusStyles';

export function HistoryPage() {
  const [sessions, setSessions] = useState<SessionHistoryItem[]>([]);
  const [q, setQ] = useState('');
  const [status, setStatus] = useState<PlanStatus | ''>('');
  const [total, setTotal] = useState(0);
  const { listSessions, isLoading } = usePlanApi();
  const navigate = useNavigate();

  useEffect(() => {
    void loadSessions();
  }, [listSessions, q, status]);

  async function loadSessions() {
    try {
      const result = await listSessions({ q, status, limit: 50 });
      setSessions(result.sessions);
      setTotal(result.total);
    } catch (error) {
      console.error('Failed to load sessions:', error);
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in duration-700">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h1 className="font-heading text-3xl font-bold tracking-tight flex items-center gap-3">
            <History className="text-primary" size={32} />
            Weave History
          </h1>
          <p className="text-text-muted font-medium">Browse and manage your previous planning sessions ({total})</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4 p-6 rounded-3xl bg-surface border border-border/40 shadow-xl glassmorphism">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-text-muted" size={18} />
          <input
            type="text"
            placeholder="Search by intent or ID..."
            className="w-full bg-surface-alt/80 border border-border/45 rounded-2xl pl-12 pr-4 py-3 text-text-body focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all duration-300"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <div className="relative w-full md:w-64">
          <Filter className="absolute left-4 top-1/2 -translate-y-1/2 text-text-muted" size={18} />
          <select
            className="w-full bg-surface-alt/80 border border-border/45 rounded-2xl pl-12 pr-10 py-3 text-text-body appearance-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all duration-300 cursor-pointer"
            value={status}
            onChange={(e) => setStatus(e.target.value as any)}
          >
            <option value="">All Statuses</option>
            <option value="BRAINSTORMING">Brainstorming</option>
            <option value="AWAITING_APPROVAL">Awaiting Approval</option>
            <option value="APPROVED">Approved</option>
            <option value="EXECUTING">Executing</option>
            <option value="COMPLETED">Completed</option>
            <option value="FAILED">Failed</option>
          </select>
        </div>
      </div>

      {isLoading('listSessions') && sessions.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 bg-surface/50 rounded-3xl border border-white/5 gap-4">
          <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center animate-pulse">
            <Activity className="text-primary animate-spin" size={24} />
          </div>
          <p className="text-text-muted font-bold tracking-widest uppercase text-xs">Retrieving Vault Data...</p>
        </div>
      ) : sessions.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 bg-surface/20 rounded-3xl border border-dashed border-white/10 text-center space-y-4">
          <Target className="text-white/10" size={64} />
          <div className="space-y-2">
            <h3 className="text-xl font-bold text-white/40">No threads found</h3>
            <p className="text-text-muted max-w-xs">Try adjusting your search filters or start a new weave.</p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sessions.map((session) => (
            <div
              key={session.session_id}
              onClick={() => navigate(`/plans/${session.session_id}`)}
              className="group p-6 rounded-3xl bg-surface border border-border/45 hover:border-primary/60 hover:bg-surface-alt/80 transition-all duration-500 cursor-pointer shadow-xl hover:shadow-primary/10 hover:-translate-y-0.5 relative overflow-hidden"
            >
              <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                <ExternalLink size={64} />
              </div>

              <div className="flex items-center justify-between mb-4">
                <div className={cn(
                  "px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest border",
                  getStatusStyles(session.status)
                )}>
                  {session.status}
                </div>
                <div className="text-[10px] font-mono text-text-muted/60 flex items-center gap-1">
                  <Clock size={10} />
                  {session.updated_at ? new Date(session.updated_at).toLocaleDateString() : 'Unknown'}
                </div>
              </div>

              <p className="text-text-body font-medium leading-relaxed italic line-clamp-3 mb-6 group-hover:text-white transition-colors">
                "{session.user_intent}"
              </p>

              <div className="flex items-center justify-between pt-4 border-t border-white/5">
                <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-tighter text-text-muted">
                  <span className="opacity-50 font-mono">ID:</span>
                  <span className="text-primary truncate max-w-[100px]">{session.session_id}</span>
                </div>
                <div className="flex items-center gap-1 text-primary text-xs font-bold opacity-0 group-hover:opacity-100 transition-all translate-x-4 group-hover:translate-x-0">
                  Open Plan
                  <ChevronRight size={14} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
