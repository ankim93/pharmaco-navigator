/**
 * Unit tests — AlertCard component
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { AlertCard } from '../../../src/components/Alerts/AlertCard';
import { redAlert, yellowAlert, greenAlert, greyAlert } from '../../fixtures';

describe('AlertCard — RED alert', () => {
  it('renders drug name in the card header', () => {
    render(<AlertCard alert={redAlert} />);
    expect(screen.getByText('Codeine')).toBeInTheDocument();
  });

  it('displays the alert colour badge', () => {
    render(<AlertCard alert={redAlert} />);
    expect(screen.getByText('RED')).toBeInTheDocument();
  });

  it('shows gene symbol and phenotype', () => {
    render(<AlertCard alert={redAlert} />);
    expect(screen.getByText('CYP2D6')).toBeInTheDocument();
    expect(screen.getByText('Poor Metabolizer')).toBeInTheDocument();
  });

  it('shows clinical recommendation text', () => {
    render(<AlertCard alert={redAlert} />);
    expect(screen.getByText(/Avoid codeine use/i)).toBeInTheDocument();
  });

  it('shows evidence classification and guideline level', () => {
    render(<AlertCard alert={redAlert} />);
    expect(screen.getByText(/Avoid Use \| Level A/i)).toBeInTheDocument();
  });
});

describe('AlertCard — YELLOW alert', () => {
  it('renders the drug name', () => {
    render(<AlertCard alert={yellowAlert} />);
    expect(screen.getByText('Clopidogrel')).toBeInTheDocument();
  });

  it('displays YELLOW badge', () => {
    render(<AlertCard alert={yellowAlert} />);
    expect(screen.getByText('YELLOW')).toBeInTheDocument();
  });
});

describe('AlertCard — GREEN alert', () => {
  it('renders the drug name', () => {
    render(<AlertCard alert={greenAlert} />);
    expect(screen.getByText('Sertraline')).toBeInTheDocument();
  });

  it('displays GREEN badge', () => {
    render(<AlertCard alert={greenAlert} />);
    expect(screen.getByText('GREEN')).toBeInTheDocument();
  });
});

describe('AlertCard — GREY alert', () => {
  it('renders the drug name', () => {
    render(<AlertCard alert={greyAlert} />);
    // Use heading role to distinguish the <h3> title from the affected-med badge
    expect(screen.getByRole('heading', { name: /Tacrolimus/i })).toBeInTheDocument();
  });

  it('shows the affected medication tag', () => {
    render(<AlertCard alert={greyAlert} />);
    // There are two instances of "Tacrolimus" – the card title and the affected-med tag
    const items = screen.getAllByText('Tacrolimus');
    expect(items.length).toBeGreaterThanOrEqual(2);
  });
});

describe('AlertCard — expand / collapse behaviour', () => {
  it('CPIC guideline link is hidden by default', () => {
    render(<AlertCard alert={redAlert} />);
    expect(screen.queryByText(/Open Full CPIC Guideline/i)).not.toBeInTheDocument();
  });

  it('clicking "View CPIC Guideline" reveals the external link', () => {
    render(<AlertCard alert={redAlert} />);
    fireEvent.click(screen.getByText(/View CPIC Guideline/i));
    expect(screen.getByText(/Open Full CPIC Guideline/i)).toBeInTheDocument();
  });

  it('clicking the button a second time hides the link again', () => {
    render(<AlertCard alert={redAlert} />);
    const btn = screen.getByText(/View CPIC Guideline/i);
    fireEvent.click(btn);
    fireEvent.click(btn);
    expect(screen.queryByText(/Open Full CPIC Guideline/i)).not.toBeInTheDocument();
  });

  it('CPIC link points to the correct URL when expanded', () => {
    render(<AlertCard alert={redAlert} />);
    fireEvent.click(screen.getByText(/View CPIC Guideline/i));
    const link = screen.getByRole('link', { name: /Open Full CPIC Guideline/i });
    expect(link).toHaveAttribute('href', redAlert.guideline_url);
  });

  it('CPIC link opens in a new tab (target=_blank)', () => {
    render(<AlertCard alert={redAlert} />);
    fireEvent.click(screen.getByText(/View CPIC Guideline/i));
    const link = screen.getByRole('link', { name: /Open Full CPIC Guideline/i });
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });
});
