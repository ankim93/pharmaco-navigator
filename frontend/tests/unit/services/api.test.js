/**
 * Unit tests — api.js service layer
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import axios from 'axios';
import { fetchPatientAlerts, fetchGenomicProfile, checkBackendHealth } from '../../../src/services/api';
import { fullAlertResponse } from '../../fixtures';

// Mock axios entirely so no real HTTP calls are made
vi.mock('axios', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    default: {
      ...actual.default,
      create: vi.fn(() => ({
        get: vi.fn(),
        interceptors: {
          response: { use: vi.fn() },
        },
      })),
    },
  };
});

// Mock the api module so no real HTTP calls are made
import * as apiModule from '../../../src/services/api';

describe('fetchPatientAlerts', () => {
  it('throws immediately when patientId is falsy', async () => {
    await expect(fetchPatientAlerts(null)).rejects.toThrow('Patient ID is required');
    await expect(fetchPatientAlerts('')).rejects.toThrow('Patient ID is required');
    await expect(fetchPatientAlerts(undefined)).rejects.toThrow('Patient ID is required');
  });
});

describe('fetchGenomicProfile', () => {
  it('throws immediately when patientId is falsy', async () => {
    await expect(fetchGenomicProfile(null)).rejects.toThrow('Patient ID is required');
  });
});
