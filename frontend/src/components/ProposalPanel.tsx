import { useState, useEffect } from 'react';
import { usePlanApi } from '../hooks/useApi';
import { Plan, StrawmanProposal } from '../types';
import { colors, disabledStyle, sharedStyles } from '../styles/ui';

interface ProposalPanelProps {
  plan: Plan;
  onSelected: () => void;
}

export function ProposalPanel({ plan, onSelected }: ProposalPanelProps) {
  const [proposals, setProposals] = useState<StrawmanProposal[]>([]);
  const { getProposals, selectProposal, isLoading, error } = usePlanApi();

  useEffect(() => {
    void loadProposals();
  }, [plan.session_id, getProposals]);

  async function loadProposals() {
    try {
      const list = await getProposals(plan.session_id);
      setProposals(list);
    } catch {}
  }

  async function handleSelect(proposalId: string) {
    try {
      await selectProposal(plan.session_id, proposalId);
      onSelected();
    } catch {}
  }

  const selecting = isLoading('selectProposal');

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Proposed Approaches</h2>
      <p style={styles.subtitle}>Review and select the best approach for your needs.</p>
      {error && <div style={styles.error}>{error}</div>}

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
              style={{ ...styles.selectButton, ...disabledStyle(selecting) }}
              onClick={() => handleSelect(p.id)}
              disabled={selecting}
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
  container: { ...sharedStyles.panel, marginBottom: '24px' },
  title: sharedStyles.sectionTitle,
  subtitle: sharedStyles.sectionSubtitle,
  error: { ...sharedStyles.errorBox, marginBottom: '16px' },
  proposals: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  proposal: {
    border: `1px solid ${colors.border}`,
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
    backgroundColor: colors.primary,
    color: colors.text,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '14px',
    fontWeight: '600',
  },
  proposalTitle: {
    fontSize: '16px',
    fontWeight: '600',
    color: colors.text,
  },
  proposalDesc: {
    color: colors.textSubtle,
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
    color: colors.textMuted,
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
    color: colors.textSubtle,
    marginBottom: '4px',
  },
  selectButton: {
    width: '100%',
    padding: '10px 16px',
    borderRadius: '6px',
    border: `1px solid ${colors.primary}`,
    backgroundColor: 'transparent',
    color: colors.primary,
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer',
  },
};
