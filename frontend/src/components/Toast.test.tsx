import { render, screen } from '@testing-library/react';
import { Toast } from './Toast';
import { vi } from 'vitest';

describe('Toast', () => {
  it('should render error toast with red styling', () => {
    render(<Toast id="1" message="Error message" type="error" onClose={() => {}} />);
    expect(screen.getByText('Error message')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveClass('bg-red-500');
  });

  it('should render success toast with green styling', () => {
    render(<Toast id="1" message="Success message" type="success" onClose={() => {}} />);
    expect(screen.getByText('Success message')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveClass('bg-green-500');
  });

  it('should render info toast with blue styling', () => {
    render(<Toast id="1" message="Info message" type="info" onClose={() => {}} />);
    expect(screen.getByText('Info message')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveClass('bg-blue-500');
  });

  it('should call onClose when dismissed', () => {
    const handleClose = vi.fn();
    render(<Toast id="1" message="Test" type="error" onClose={handleClose} />);
    const closeButton = screen.getByRole('button');
    closeButton.click();
    expect(handleClose).toHaveBeenCalled();
  });
});
