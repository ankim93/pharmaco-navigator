/**
 * Vitest + React Testing Library global setup.
 * Includes MSW v2 server for request interception in unit/integration tests.
 */

import '@testing-library/jest-dom';
import { afterEach, beforeAll, afterAll } from 'vitest';
import { cleanup } from '@testing-library/react';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';

const DEMO_ALERTS_RESPONSE = {
  patient_id: 'DEMO001',
  total_medications: 4,
  active_medications: ['Codeine', 'Clopidogrel', 'Sertraline', 'Tacrolimus'],
  red_alerts: [
    {
      drug_name: 'Codeine',
      gene_symbol: 'CYP2D6',
      phenotype: 'Poor Metabolizer',
      alert_color: 'RED',
      classification: 'Avoid Use',
      guideline_level: 'A',
      clinical_action: 'Avoid codeine use due to lack of CYP2D6 enzyme activity.',
      guideline_url: 'https://cpicpgx.org/guidelines/guideline-for-codeine-and-cyp2d6/',
      affected_medications: [],
    },
  ],
  yellow_alerts: [],
  green_alerts: [],
  grey_alerts: [],
};

export const handlers = [
  http.get('/api/v1/patient/:patientId/alerts', ({ params }) => {
    if (params.patientId === 'DEMO_ERROR') {
      return HttpResponse.json({ detail: 'Patient not found' }, { status: 404 });
    }
    if (params.patientId === 'DEMO_503') {
      return HttpResponse.json({ detail: 'Service unavailable' }, { status: 503 });
    }
    return HttpResponse.json({
      ...DEMO_ALERTS_RESPONSE,
      patient_id: params.patientId,
    });
  }),

  http.get('/api/v1/health', () => {
    return HttpResponse.json({ status: 'healthy', version: '2.0.0' });
  }),
];

export const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));
afterEach(() => {
  server.resetHandlers();
  cleanup();
});
afterAll(() => server.close());
