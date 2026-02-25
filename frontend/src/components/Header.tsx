import { NavLink } from 'react-router-dom';
import { colors } from '../styles/ui';

export function Header() {
  return (
    <header style={styles.header}>
      <div style={styles.logo}>
        <span style={styles.logoIcon}>🕸️</span>
        <span style={styles.logoText}>PlanWeaver</span>
      </div>
      <nav style={styles.nav}>
        <NavLink to="/" style={getNavLinkStyle}>New Plan</NavLink>
        <NavLink to="/history" style={getNavLinkStyle}>History</NavLink>
      </nav>
    </header>
  );
}

function getNavLinkStyle({ isActive }: { isActive: boolean }) {
  return {
    ...styles.navLink,
    color: isActive ? colors.text : styles.navLink.color,
  };
}

const styles: Record<string, React.CSSProperties> = {
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 24px',
    backgroundColor: '#1a1a2e',
    borderBottom: `1px solid ${colors.borderMuted}`,
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  logoIcon: {
    fontSize: '24px',
  },
  logoText: {
    fontSize: '20px',
    fontWeight: '600',
    color: colors.text,
  },
  nav: {
    display: 'flex',
    gap: '24px',
  },
  navLink: {
    color: colors.textMuted,
    textDecoration: 'none',
    fontSize: '14px',
  },
};
