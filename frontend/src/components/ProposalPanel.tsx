import { useState, useEffect } from 'react';
import { usePlanApi } from '../hooks/useApi';
import { Plan } from '../types';

interface ProposalPanelProps {
  plan: Plan;
  onSelected: () => void;
}

export function ProposalPanel({ plan, onSelected }: ProposalPanelProps) {
  const [proposals, setProposals] = useState<any[]>([]);
  const { getProposals, selectProposal, loading } = usePlanApi();

  useEffect(() => {
    loadProposals();
  }, [plan.session_id]);

  async function loadProposals() {
    try {
      const list = await getProposals(plan.session_id);
      setProposals(list);
    } catch (e) {
      console.error('Failed to load proposals');
    }
  }

  async function handleSelect(proposalId: string) {
    await selectProposal(plan.session_id, proposalId);
    onSelected();
  }

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Proposed Approaches</h2>
      <p style={styles.subtitle}>Review and select the best approach for your needs.</p>

      <div style={styles.proposals}>
        {proposals.map((p, i) => (
          <div key={p.id} style={styles.proposal}>
            <div style={styles.proposalHeader}>
              <span style={styles.proposalNumber}>{i + 1}</span>
              <h3 style={styles.proposalTitle}>{p.title}</h3>
            </div>
            <p style={styles.proposalDesc}>{p.description}</p>

            <div style={styles.prosCons}>
              <div style={styles.pros}>
                <span style={styles.prosConsLabel}>Pros</span>
                <ul style={styles.list}>
                  {p.pros.map((pro: string, j: number) => (
                    <li key={j} style={styles.listItem}>+ {pro}</li>
                  ))}
                </ul>
              </div>
              <div style={styles.cons}>
                <span style={styles.prosConsLabel}>Cons</span>
                <ul style={styles.list}>
                  {p.cons.map((con: string, j: number) => (
                    <li key={j} style={styles.listItem}>- {con}</li>
                  ))}
                </ul>
              </div>
            </div>

            <button
              style={styles.selectButton}
              onClick={() => handleSelect(p.id)}
              disabled={loading}
            >
              Select This Approach
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    backgroundColor: '#1e1e36',
    borderRadius: '12px',
    padding: '24px',
    marginBottom: '24px',
  },
  title: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#fff',
    marginBottom: '4px',
  },
  subtitle: {
    color: '#a0a0b0',
    fontSize: '14px',
    marginBottom: '20px',
  },
  proposals: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  proposal: {
    border: '1px solid #3d3d5c',
    borderRadius: '8px',
    padding: '20px',
  },
  proposalHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '12px',
  },
  proposalNumber: {
    width: '28px',
    height: '28px',
    borderRadius: '50%',
    backgroundColor: '#6366f1',
    color: '#fff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '14px',
    fontWeight: '600',
  },
  proposalTitle: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#fff',
  },
  proposalDesc: {
    color: '#c0c0d0',
    fontSize: '14px',
    marginBottom: '16px',
  },
  prosCons: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '16px',
    marginBottom: '16px',
  },
  pros: {},
  cons: {},
  prosConsLabel: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#a0a0b0',
    textTransform: 'uppercase',
    marginBottom: '8px',
    display: 'block',
  },
  list: {
    listStyle: 'none',
    padding: 0,
    margin: 0,
  },
  listItem: {
    fontSize: '13px',
    color: '#c0c0d0',
    marginBottom: '4px',
  },
  selectButton: {
    width: '100%',
    padding: '10px 16px',
    borderRadius: '6px',
    border: '1px solid #6366f1',
    backgroundColor: 'transparent',
    color: '#6366f1',
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer',
  },
};
