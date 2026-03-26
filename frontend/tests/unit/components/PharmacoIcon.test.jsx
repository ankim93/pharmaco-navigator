/**
 * Unit tests — PharmacoIcon custom SVG component
 */

import React from 'react';
import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PharmacoIcon } from '../../../src/components/Commons/PharmacoIcon';

describe('PharmacoIcon', () => {
  it('renders an SVG element', () => {
    const { container } = render(<PharmacoIcon />);
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('applies the default className (h-8 w-8)', () => {
    const { container } = render(<PharmacoIcon />);
    expect(container.querySelector('svg')).toHaveClass('h-8', 'w-8');
  });

  it('accepts a custom className override', () => {
    const { container } = render(<PharmacoIcon className="h-12 w-12 text-white" />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveClass('h-12', 'w-12', 'text-white');
    expect(svg).not.toHaveClass('h-8', 'w-8');
  });

  it('has aria-label for screen readers', () => {
    const { container } = render(<PharmacoIcon />);
    expect(container.querySelector('svg')).toHaveAttribute('aria-label', 'Pharmaco-Navigator');
  });

  it('uses currentColor stroke so it inherits text colour from parent', () => {
    const { container } = render(<PharmacoIcon />);
    expect(container.querySelector('svg')).toHaveAttribute('stroke', 'currentColor');
  });

  it('renders the pill capsule path element', () => {
    const { container } = render(<PharmacoIcon />);
    const paths = container.querySelectorAll('svg path');
    expect(paths.length).toBeGreaterThanOrEqual(1);
  });
});
