/**
 * Unit tests — DashboardHeader component
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { DashboardHeader } from '../../../src/components/Dashboard/DashboardHeader';
import { geneSummary } from '../../fixtures';

const defaultProps = {
  patientId: 'DEMO001',
  geneSummary,
  totalMedications: 4,
};

describe('DashboardHeader — basic rendering', () => {
  it('displays the app title', () => {
    render(<DashboardHeader {...defaultProps} />);
    expect(screen.getByText('Pharmaco-Navigator')).toBeInTheDocument();
  });

  it('displays the subtitle', () => {
    render(<DashboardHeader {...defaultProps} />);
    expect(screen.getByText(/Clinical Decision Support System/i)).toBeInTheDocument();
  });

  it('displays the patient ID', () => {
    render(<DashboardHeader {...defaultProps} />);
    expect(screen.getByText('DEMO001')).toBeInTheDocument();
  });

  it('renders the Pharmacogenomic Profile section heading', () => {
    render(<DashboardHeader {...defaultProps} />);
    expect(screen.getByText('Pharmacogenomic Profile')).toBeInTheDocument();
  });
});

describe('DashboardHeader — gene status badges', () => {
  it('renders all four gene names', () => {
    render(<DashboardHeader {...defaultProps} />);
    expect(screen.getByText('CYP2D6')).toBeInTheDocument();
    expect(screen.getByText('CYP2C19')).toBeInTheDocument();
    expect(screen.getByText('SLCO1B1')).toBeInTheDocument();
    expect(screen.getByText('ABCB1')).toBeInTheDocument();
  });

  it('shows phenotype for CYP2D6', () => {
    render(<DashboardHeader {...defaultProps} />);
    expect(screen.getByText('Poor Metabolizer')).toBeInTheDocument();
  });

  it('shows phenotype for CYP2C19', () => {
    render(<DashboardHeader {...defaultProps} />);
    expect(screen.getByText('Intermediate Metabolizer')).toBeInTheDocument();
  });

  it('shows Data Missing for ABCB1 (hasGuidelines=false)', () => {
    render(<DashboardHeader {...defaultProps} />);
    // ABCB1 hasGuidelines:false → "Data Missing/Unknown" displayed
    expect(screen.getByText('Data Missing/Unknown')).toBeInTheDocument();
  });

  it('shows "no active med alerts" for a gene with zero counts', () => {
    render(<DashboardHeader {...defaultProps} />);
    // ABCB1 has 0 red/yellow/green — should show the italic no-alerts label
    const noAlertMsgs = screen.getAllByText(/no active med alerts/i);
    expect(noAlertMsgs.length).toBeGreaterThanOrEqual(1);
  });
});

describe('DashboardHeader — medications info text', () => {
  it('shows total medications count', () => {
    render(<DashboardHeader {...defaultProps} />);
    expect(screen.getByText(/4 medication/i)).toBeInTheDocument();
  });

  it('renders with zero medications gracefully', () => {
    render(<DashboardHeader {...defaultProps} totalMedications={0} />);
    expect(screen.getByText(/0 medication/i)).toBeInTheDocument();
  });

  it('uses singular "medication" for count of 1', () => {
    render(<DashboardHeader {...defaultProps} totalMedications={1} />);
    expect(screen.getByText(/1 medication[^s]/i)).toBeInTheDocument();
  });
});
