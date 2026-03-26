/**
 * Unit tests — AlertGrid component
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { AlertGrid } from '../../../src/components/Alerts/AlertGrid';
import {
  fullAlertResponse,
  safePatientResponse,
  emptyAlertResponse,
} from '../../fixtures';

describe('AlertGrid — full alert response', () => {
  it('renders the High Risk section heading', () => {
    render(<AlertGrid alerts={fullAlertResponse} />);
    expect(screen.getByText('High Risk')).toBeInTheDocument();
  });

  it('renders the Moderate Risk section heading', () => {
    render(<AlertGrid alerts={fullAlertResponse} />);
    expect(screen.getByText('Moderate Risk')).toBeInTheDocument();
  });

  it('renders the Safe / Standard Dosing heading', () => {
    render(<AlertGrid alerts={fullAlertResponse} />);
    expect(screen.getByText('Safe / Standard Dosing')).toBeInTheDocument();
  });

  it('renders the Data Missing/Unknown heading when grey alerts exist', () => {
    render(<AlertGrid alerts={fullAlertResponse} />);
    // The text also appears in the grey card's phenotype badge — target the <h2> by role
    expect(
      screen.getByRole('heading', { name: /Data Missing\/Unknown/i })
    ).toBeInTheDocument();
  });

  it('shows correct count (1) beside each section', () => {
    render(<AlertGrid alerts={fullAlertResponse} />);
    // Each section shows "(1)"
    const counts = screen.getAllByText('(1)');
    expect(counts.length).toBe(4);
  });

  it('renders the drug names from all buckets', () => {
    render(<AlertGrid alerts={fullAlertResponse} />);
    expect(screen.getByText('Codeine')).toBeInTheDocument();
    expect(screen.getByText('Clopidogrel')).toBeInTheDocument();
    expect(screen.getByText('Sertraline')).toBeInTheDocument();
    // Tacrolimus appears in card title + affected medications list
    expect(screen.getAllByText('Tacrolimus').length).toBeGreaterThanOrEqual(1);
  });
});

describe('AlertGrid — safe patient (no red/yellow/grey alerts)', () => {
  it('shows empty-state message for High Risk column', () => {
    render(<AlertGrid alerts={safePatientResponse} />);
    expect(
      screen.getByText(/No high-risk drug interactions detected/i)
    ).toBeInTheDocument();
  });

  it('shows empty-state message for Moderate Risk column', () => {
    render(<AlertGrid alerts={safePatientResponse} />);
    expect(
      screen.getByText(/No moderate-risk interactions detected/i)
    ).toBeInTheDocument();
  });

  it('does NOT render the Data Missing/Unknown column', () => {
    render(<AlertGrid alerts={safePatientResponse} />);
    expect(screen.queryByText('Data Missing/Unknown')).not.toBeInTheDocument();
  });
});

describe('AlertGrid — empty response', () => {
  it('shows empty-state messages in all three main columns', () => {
    render(<AlertGrid alerts={emptyAlertResponse} />);
    expect(
      screen.getByText(/No high-risk drug interactions detected/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/No moderate-risk interactions detected/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/No medications cleared for standard dosing/i)
    ).toBeInTheDocument();
  });
});
