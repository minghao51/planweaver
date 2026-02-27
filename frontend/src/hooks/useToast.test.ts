import { renderHook, act } from '@testing-library/react';
import { useToast } from './useToast';
import { vi } from 'vitest';

describe('useToast', () => {
  it('should add error toast', () => {
    const { result } = renderHook(() => useToast());
    act(() => {
      result.current.error('Test error');
    });
    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].message).toBe('Test error');
    expect(result.current.toasts[0].type).toBe('error');
  });

  it('should add success toast', () => {
    const { result } = renderHook(() => useToast());
    act(() => {
      result.current.success('Test success');
    });
    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].type).toBe('success');
  });

  it('should add info toast', () => {
    const { result } = renderHook(() => useToast());
    act(() => {
      result.current.info('Test info');
    });
    expect(result.current.toasts).toHaveLength(1);
    expect(result.current.toasts[0].type).toBe('info');
  });

  it('should auto-dismiss after 5 seconds', () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useToast());
    act(() => {
      result.current.error('Test');
    });
    expect(result.current.toasts).toHaveLength(1);
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(result.current.toasts).toHaveLength(0);
    vi.useRealTimers();
  });

  it('should remove toast manually', () => {
    const { result } = renderHook(() => useToast());
    act(() => {
      result.current.error('Test');
    });
    expect(result.current.toasts).toHaveLength(1);

    const toastId = result.current.toasts[0].id;
    act(() => {
      result.current.remove(toastId);
    });
    expect(result.current.toasts).toHaveLength(0);
  });
});
