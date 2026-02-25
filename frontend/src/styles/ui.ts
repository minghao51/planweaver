import type { CSSProperties } from 'react';

export const colors = {
  bg: '#0d0d1a',
  surface: '#1e1e36',
  surfaceAlt: '#16162a',
  surfaceMuted: '#0f0f1a',
  border: '#3d3d5c',
  borderMuted: '#2d2d44',
  text: '#ffffff',
  textMuted: '#a0a0b0',
  textBody: '#e0e0e0',
  textSubtle: '#c0c0d0',
  primary: '#6366f1',
  success: '#22c55e',
  successSoft: '#10b981',
  warning: '#f59e0b',
  info: '#3b82f6',
  violet: '#8b5cf6',
  danger: '#ef4444',
  dangerBg: '#2d1f1f',
  dangerText: '#ff6b6b',
  gray: '#6b7280',
} as const;

export const sharedStyles = {
  pageContainer: {
    maxWidth: '900px',
    margin: '0 auto',
    padding: '24px',
  } satisfies CSSProperties,
  panel: {
    backgroundColor: colors.surface,
    borderRadius: '12px',
    padding: '24px',
  } satisfies CSSProperties,
  fieldLabel: {
    color: colors.textBody,
    fontSize: '14px',
    fontWeight: 500,
  } satisfies CSSProperties,
  inputBase: {
    padding: '12px 16px',
    borderRadius: '8px',
    border: `1px solid ${colors.border}`,
    backgroundColor: colors.surfaceAlt,
    color: colors.text,
    fontSize: '14px',
  } satisfies CSSProperties,
  sectionTitle: {
    fontSize: '18px',
    fontWeight: 600,
    color: colors.text,
    marginBottom: '4px',
  } satisfies CSSProperties,
  sectionSubtitle: {
    color: colors.textMuted,
    fontSize: '14px',
    marginBottom: '20px',
  } satisfies CSSProperties,
  primaryButton: {
    padding: '12px 24px',
    borderRadius: '8px',
    border: 'none',
    backgroundColor: colors.primary,
    color: colors.text,
    fontSize: '14px',
    fontWeight: 500,
    cursor: 'pointer',
  } satisfies CSSProperties,
  errorBox: {
    padding: '12px 16px',
    borderRadius: '8px',
    backgroundColor: colors.dangerBg,
    color: colors.dangerText,
    fontSize: '14px',
  } satisfies CSSProperties,
};

export function disabledStyle(disabled: boolean): CSSProperties {
  return disabled ? { opacity: 0.5, cursor: 'not-allowed' } : {};
}
