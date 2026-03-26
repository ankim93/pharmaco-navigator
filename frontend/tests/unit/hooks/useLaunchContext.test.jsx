/**
 * Unit tests — useLaunchContext hook
 */

import { renderHook } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import { useLaunchContext } from '../../../src/hooks/useLaunchContext';

/**
 * Wrapper that puts the hook inside a MemoryRouter with provided search params.
 */
const makeWrapper = (search) =>
  ({ children }) => (
    <MemoryRouter initialEntries={[`/${search}`]}>{children}</MemoryRouter>
  );

describe('useLaunchContext — patient extraction', () => {
  it('extracts patient ID from ?patient= parameter', () => {
    const { result } = renderHook(() => useLaunchContext(), {
      wrapper: makeWrapper('?patient=DEMO001'),
    });
    expect(result.current.patientId).toBe('DEMO001');
    expect(result.current.isReady).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it('extracts patient ID from ?patient_id= parameter', () => {
    const { result } = renderHook(() => useLaunchContext(), {
      wrapper: makeWrapper('?patient_id=12724067'),
    });
    expect(result.current.patientId).toBe('12724067');
    expect(result.current.isReady).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it('trims leading and trailing whitespace from patient ID', () => {
    const { result } = renderHook(() => useLaunchContext(), {
      wrapper: makeWrapper('?patient=%20DEMO001%20'),
    });
    expect(result.current.patientId).toBe('DEMO001');
  });

  it('prefers ?patient= over ?patient_id= when both are present', () => {
    const { result } = renderHook(() => useLaunchContext(), {
      wrapper: makeWrapper('?patient=A&patient_id=B'),
    });
    expect(result.current.patientId).toBe('A');
  });
});

describe('useLaunchContext — error states', () => {
  it('sets error when no patient parameter is provided', () => {
    const { result } = renderHook(() => useLaunchContext(), {
      wrapper: makeWrapper(''),
    });
    expect(result.current.patientId).toBeNull();
    expect(result.current.error).toMatch(/Missing patient parameter/i);
    expect(result.current.isReady).toBe(true);
  });

  it('sets error when patient param is empty string', () => {
    const { result } = renderHook(() => useLaunchContext(), {
      wrapper: makeWrapper('?patient='),
    });
    expect(result.current.patientId).toBeNull();
    expect(result.current.error).toMatch(/Missing patient parameter/i);
    expect(result.current.isReady).toBe(true);
  });
});
