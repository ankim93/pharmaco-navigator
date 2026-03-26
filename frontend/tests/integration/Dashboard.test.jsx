/**
 * Integration tests — Dashboard component
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { Dashboard } from '../../src/components/Dashboard/Dashboard';
import { fullAlertResponse, safePatientResponse } from '../fixtures';

// API mock setup - no real HTTP calls are made.

vi.mock('../../src/services/api', () => ({
  fetchPatientAlerts: vi.fn(),
}));

import { fetchPatientAlerts } from '../../src/services/api';

/**
 * Renders Dashboard inside a MemoryRouter with the given URL search params.
 */
const renderDashboard = (search = '?patient=DEMO001') =>
  render(
    <MemoryRouter initialEntries={[`/${search}`]}>
      <Dashboard />
    </MemoryRouter>
  );


// Tests
describe('Dashboard — loading state', () => {
  it('shows the loading spinner while the API call is in progress', async () => {
    // Never resolves during this test
    fetchPatientAlerts.mockReturnValue(new Promise(() => {}));
    renderDashboard();
    // The loading text appears after the useLaunchContext effect fires — use findByText
    const spinner = await screen.findByText(/Loading clinical decision support data/i);
    expect(spinner).toBeInTheDocument();
  });
});

describe('Dashboard — successful data load', () => {
  beforeEach(() => {
    fetchPatientAlerts.mockResolvedValue(fullAlertResponse);
  });

  it('renders the DashboardHeader with the patient ID', async () => {
    renderDashboard();
    await waitFor(() =>
      expect(screen.getByText('DEMO001')).toBeInTheDocument()
    );
  });

  it('renders the app title', async () => {
    renderDashboard();
    await waitFor(() =>
      expect(screen.getByText('Pharmaco-Navigator')).toBeInTheDocument()
    );
  });

  it('displays the active medications panel', async () => {
    renderDashboard();
    // The panel heading reads "Active Medications (N)" — target by heading role
    // to avoid matching alert card's "Affected Active Medications:" label
    await waitFor(() =>
      expect(
        screen.getByRole('heading', { name: /^Active Medications/i })
      ).toBeInTheDocument()
    );
  });

  it('shows each active medication as a pill badge', async () => {
    renderDashboard();
    // Meds appear in both the pill badges AND the alert card headings.
    // getAllByText confirms each name is present at least once.
    await waitFor(() => {
      expect(screen.getAllByText('Codeine').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Clopidogrel').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Sertraline').length).toBeGreaterThanOrEqual(1);
    });
  });

  it('renders the alert grid with all four section headings', async () => {
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText('High Risk')).toBeInTheDocument();
      expect(screen.getByText('Moderate Risk')).toBeInTheDocument();
      expect(screen.getByText('Safe / Standard Dosing')).toBeInTheDocument();
      // 'Data Missing/Unknown' also appears in the grey card phenotype badge — use heading role
      expect(
        screen.getByRole('heading', { name: /Data Missing\/Unknown/i })
      ).toBeInTheDocument();
    });
  });

  it('renders the CPIC footer text', async () => {
    renderDashboard();
    await waitFor(() =>
      expect(
        screen.getByText(/Clinical Decision Support System based on CPIC/i)
      ).toBeInTheDocument()
    );
  });

  it('calls fetchPatientAlerts with the patient ID from URL', async () => {
    renderDashboard('?patient=DEMO001');
    await waitFor(() => expect(fetchPatientAlerts).toHaveBeenCalledWith('DEMO001'));
  });
});

describe('Dashboard — safe patient (no high-risk alerts)', () => {
  beforeEach(() => {
    fetchPatientAlerts.mockResolvedValue(safePatientResponse);
  });

  it('shows empty-state for High Risk column', async () => {
    renderDashboard('?patient=DEMO002');
    await waitFor(() =>
      expect(
        screen.getByText(/No high-risk drug interactions detected/i)
      ).toBeInTheDocument()
    );
  });

  it('does not render the Data Missing/Unknown column', async () => {
    renderDashboard('?patient=DEMO002');
    await waitFor(() =>
      expect(screen.queryByText('Data Missing/Unknown')).not.toBeInTheDocument()
    );
  });
});

describe('Dashboard — API error state', () => {
  beforeEach(() => {
    fetchPatientAlerts.mockRejectedValue(
      new Error('Network error - unable to connect to backend server')
    );
  });

  it('shows the error alert component', async () => {
    renderDashboard();
    await waitFor(() =>
      expect(screen.getByText(/Backend Connection Error/i)).toBeInTheDocument()
    );
  });

  it('shows the Retry Connection button', async () => {
    renderDashboard();
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Retry Connection/i })).toBeInTheDocument()
    );
  });
});

describe('Dashboard — missing patient parameter', () => {
  it('shows the SMART Launch Context Error when no patient param is given', async () => {
    renderDashboard('');
    await waitFor(() =>
      expect(screen.getByText(/SMART Launch Context Error/i)).toBeInTheDocument()
    );
  });
});
