export function Header() {
  return (
    <header style={styles.header}>
      <div style={styles.logo}>
        <span style={styles.logoIcon}>🕸️</span>
        <span style={styles.logoText}>PlanWeaver</span>
      </div>
      <nav style={styles.nav}>
        <a href="/" style={styles.navLink}>New Plan</a>
        <a href="/history" style={styles.navLink}>History</a>
      </nav>
    </header>
  );
}

const styles: Record<string, React.CSSProperties> = {
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 24px',
    backgroundColor: '#1a1a2e',
    borderBottom: '1px solid #2d2d44',
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
    color: '#fff',
  },
  nav: {
    display: 'flex',
    gap: '24px',
  },
  navLink: {
    color: '#a0a0b0',
    textDecoration: 'none',
    fontSize: '14px',
  },
};
