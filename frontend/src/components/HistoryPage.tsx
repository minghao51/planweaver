import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { usePlanApi } from '../hooks/useApi';
import { PlanStatus, SessionHistoryItem } from '../types';
import { colors, sharedStyles, disabledStyle } from '../styles/ui';

const PAGE_SIZE = 10;
const STATUS_OPTIONS: Array<{ label: string; value: '' | PlanStatus }> = [
  { label: 'All statuses', value: '' },
  { label: 'Brainstorming', value: 'BRAINSTORMING' },
  { label: 'Awaiting Approval', value: 'AWAITING_APPROVAL' },
  { label: 'Approved', value: 'APPROVED' },
  { label: 'Executing', value: 'EXECUTING' },
  { label: 'Completed', value: 'COMPLETED' },
  { label: 'Failed', value: 'FAILED' },
];

export function HistoryPage() {
  const [sessions, setSessions] = useState<SessionHistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [status, setStatus] = useState<'' | PlanStatus>('');
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const { listSessions, isLoading, error } = usePlanApi();

  useEffect(() => {
    void loadSessions();
  }, [listSessions, offset, status, searchQuery]);

  async function loadSessions() {
    try {
      const result = await listSessions({
        limit: PAGE_SIZE,
        offset,
        status,
        q: searchQuery,
      });
      setSessions(result.sessions);
      setTotal(result.total);
    } catch {}
  }

  function applyFilters() {
    setOffset(0);
    setSearchQuery(searchInput.trim());
  }

  function clearFilters() {
    setSearchInput('');
    setSearchQuery('');
    setStatus('');
    setOffset(0);
  }

  const loading = isLoading('listSessions');
  const pageStart = sessions.length === 0 ? 0 : offset + 1;
  const pageEnd = offset + sessions.length;
  const canPrev = offset > 0;
  const canNext = offset + PAGE_SIZE < total;

  return (
    <section style={styles.container}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>History</h1>
          <p style={styles.subtitle}>Recent planning sessions and their current status.</p>
        </div>
        <button
          type="button"
          onClick={() => void loadSessions()}
          style={{ ...styles.refreshButton, ...disabledStyle(loading) }}
          disabled={loading}
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      <div style={styles.filters}>
        <input
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search intent or scenario..."
          style={styles.searchInput}
        />
        <select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value as '' | PlanStatus);
            setOffset(0);
          }}
          style={styles.statusSelect}
        >
          {STATUS_OPTIONS.map((option) => (
            <option key={option.label} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <button type="button" onClick={applyFilters} style={styles.filterButton}>
          Apply
        </button>
        <button type="button" onClick={clearFilters} style={styles.secondaryButton}>
          Clear
        </button>
      </div>

      {error && <div style={styles.error}>{error}</div>}

      <div style={styles.summaryRow}>
        <span style={styles.summaryText}>
          {total === 0 ? 'No results' : `Showing ${pageStart}-${pageEnd} of ${total}`}
        </span>
        <div style={styles.pagination}>
          <button
            type="button"
            onClick={() => setOffset((value) => Math.max(0, value - PAGE_SIZE))}
            disabled={!canPrev || loading}
            style={{ ...styles.secondaryButton, ...disabledStyle(!canPrev || loading) }}
          >
            Previous
          </button>
          <button
            type="button"
            onClick={() => setOffset((value) => value + PAGE_SIZE)}
            disabled={!canNext || loading}
            style={{ ...styles.secondaryButton, ...disabledStyle(!canNext || loading) }}
          >
            Next
          </button>
        </div>
      </div>

      {sessions.length === 0 && !loading ? (
        <div style={styles.empty}>No sessions yet.</div>
      ) : (
        <div style={styles.list}>
          {sessions.map((session) => (
            <article key={session.session_id} style={styles.card}>
              <div style={styles.cardTop}>
                <span style={{ ...styles.status, backgroundColor: getStatusColor(session.status) }}>
                  {session.status}
                </span>
                <span style={styles.time}>
                  Updated {formatDateTime(session.updated_at)}
                </span>
              </div>

              <p style={styles.intent}>{session.user_intent}</p>

              <div style={styles.meta}>
                <span>Session: {session.session_id}</span>
                <span>Scenario: {session.scenario_name || 'Auto'}</span>
                <span>Created: {formatDateTime(session.created_at)}</span>
              </div>

              <Link to={`/plans/${session.session_id}`} style={styles.openLink}>
                Open plan
              </Link>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function formatDateTime(value?: string | null) {
  if (!value) return 'Unknown';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Unknown';
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function getStatusColor(status: SessionHistoryItem['status']) {
  switch (status) {
    case 'BRAINSTORMING':
      return colors.warning;
    case 'AWAITING_APPROVAL':
      return colors.info;
    case 'APPROVED':
      return colors.success;
    case 'EXECUTING':
      return colors.violet;
    case 'COMPLETED':
      return colors.successSoft;
    case 'FAILED':
      return colors.danger;
    default:
      return colors.gray;
  }
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    ...sharedStyles.pageContainer,
    paddingTop: '24px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '16px',
    marginBottom: '20px',
  },
  title: {
    margin: 0,
    color: colors.text,
    fontSize: '24px',
    fontWeight: 600,
  },
  subtitle: {
    margin: '8px 0 0',
    color: colors.textMuted,
    fontSize: '14px',
  },
  refreshButton: {
    ...sharedStyles.primaryButton,
    padding: '10px 14px',
  },
  filters: {
    display: 'grid',
    gridTemplateColumns: 'minmax(220px, 1fr) auto auto auto',
    gap: '8px',
    alignItems: 'center',
    marginBottom: '16px',
  },
  searchInput: {
    ...sharedStyles.inputBase,
    minWidth: 0,
  },
  statusSelect: {
    ...sharedStyles.inputBase,
    backgroundColor: colors.surfaceAlt,
  },
  filterButton: {
    ...sharedStyles.primaryButton,
    padding: '10px 14px',
  },
  secondaryButton: {
    padding: '10px 14px',
    borderRadius: '8px',
    border: `1px solid ${colors.border}`,
    backgroundColor: 'transparent',
    color: colors.textBody,
    cursor: 'pointer',
    fontSize: '14px',
  },
  error: {
    ...sharedStyles.errorBox,
    marginBottom: '16px',
  },
  summaryRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '12px',
  },
  summaryText: {
    color: colors.textMuted,
    fontSize: '13px',
  },
  pagination: {
    display: 'flex',
    gap: '8px',
  },
  empty: {
    ...sharedStyles.panel,
    color: colors.textMuted,
  },
  list: {
    display: 'grid',
    gap: '12px',
  },
  card: {
    ...sharedStyles.panel,
    padding: '16px',
    border: `1px solid ${colors.borderMuted}`,
  },
  cardTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '10px',
  },
  status: {
    color: colors.text,
    borderRadius: '999px',
    padding: '4px 10px',
    fontSize: '12px',
    fontWeight: 600,
  },
  time: {
    color: colors.textMuted,
    fontSize: '12px',
  },
  intent: {
    margin: '0 0 12px',
    color: colors.textBody,
    lineHeight: 1.5,
  },
  meta: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px 16px',
    color: colors.gray,
    fontSize: '12px',
    marginBottom: '12px',
  },
  openLink: {
    color: colors.primary,
    textDecoration: 'none',
    fontWeight: 500,
    fontSize: '14px',
  },
};
