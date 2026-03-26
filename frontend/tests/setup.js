/**
 * Vitest + React Testing Library global setup.
 */

import '@testing-library/jest-dom';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

// Auto-unmount React trees after every test to prevent leaks
afterEach(() => {
  cleanup();
});
