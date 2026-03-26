/**
 * Unit tests — ErrorAlert component
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ErrorAlert } from '../../../src/components/Commons/ErrorAlert';

const genericError = new Error('An unexpected error occurred');
const networkError = new Error('Network error - unable to connect to backend server');

describe('ErrorAlert — generic error', () => {
  it('renders the error title', () => {
    render(<ErrorAlert error={genericError} />);
    expect(screen.getByText(/Unable to Load Clinical Data/i)).toBeInTheDocument();
  });

  it('renders the error message', () => {
    render(<ErrorAlert error={genericError} />);
    expect(screen.getByText(/An unexpected error occurred/i)).toBeInTheDocument();
  });

  it('does not show retry button when onRetry is not provided', () => {
    render(<ErrorAlert error={genericError} />);
    expect(screen.queryByRole('button', { name: /retry/i })).not.toBeInTheDocument();
  });

  it('does not show the backend URL hint', () => {
    render(<ErrorAlert error={genericError} />);
    expect(screen.queryByText(/localhost:8000/i)).not.toBeInTheDocument();
  });
});

describe('ErrorAlert — connection error', () => {
  it('renders the connection-specific title', () => {
    render(<ErrorAlert error={networkError} />);
    expect(screen.getByText(/Backend Connection Error/i)).toBeInTheDocument();
  });

  it('shows the backend URL hint', () => {
    render(<ErrorAlert error={networkError} />);
    expect(screen.getByText(/localhost:8000/i)).toBeInTheDocument();
  });
});

describe('ErrorAlert — retry interaction', () => {
  it('renders the Retry Connection button when onRetry is provided', () => {
    render(<ErrorAlert error={genericError} onRetry={() => {}} />);
    expect(screen.getByRole('button', { name: /Retry Connection/i })).toBeInTheDocument();
  });

  it('calls onRetry when the retry button is clicked', () => {
    const onRetry = vi.fn();
    render(<ErrorAlert error={genericError} onRetry={onRetry} />);
    fireEvent.click(screen.getByRole('button', { name: /Retry Connection/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
