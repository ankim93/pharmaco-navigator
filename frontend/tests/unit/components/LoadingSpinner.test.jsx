/**
 * Unit tests — LoadingSpinner component
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { LoadingSpinner } from '../../../src/components/Commons/LoadingSpinner';

describe('LoadingSpinner', () => {
  it('renders the default message', () => {
    render(<LoadingSpinner />);
    expect(screen.getByText(/Loading clinical data/i)).toBeInTheDocument();
  });

  it('renders a custom message when provided', () => {
    render(<LoadingSpinner message="Initializing dashboard..." />);
    expect(screen.getByText('Initializing dashboard...')).toBeInTheDocument();
  });

  it('renders the spinner icon element', () => {
    const { container } = render(<LoadingSpinner />);
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('applies animate-spin class to the icon', () => {
    const { container } = render(<LoadingSpinner />);
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });
});
