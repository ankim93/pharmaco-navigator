/**
 * SMART on FHIR Launch Context Hook
 * Extracts and sanitizes EHR launch parameters (iss, launch) and post-auth
 * patient ID from URL search params before triggering presentation hooks.
 */

import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';

const SAFE_HTTPS_RE = /^https:\/\/.+/i;

const sanitizeIss = (raw) => {
  if (!raw) return null;
  const trimmed = raw.trim();
  return SAFE_HTTPS_RE.test(trimmed) ? trimmed : null;
};

const sanitizeLaunchToken = (raw) => {
  if (!raw) return null;
  const trimmed = raw.trim();
  return trimmed.length > 0 ? trimmed : null;
};

export const useLaunchContext = () => {
  const [searchParams] = useSearchParams();
  const [patientId, setPatientId] = useState(null);
  const [iss, setIss] = useState(null);
  const [launch, setLaunch] = useState(null);
  const [launchMode, setLaunchMode] = useState(null);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    try {
      const rawIss = searchParams.get('iss');
      const rawLaunch = searchParams.get('launch');

      if (rawIss || rawLaunch) {
        // EHR launch phase: sanitize iss and launch before passing to auth flow
        const safeIss = sanitizeIss(rawIss);
        const safeLaunch = sanitizeLaunchToken(rawLaunch);

        if (!safeIss) {
          setError('Invalid EHR launch: iss must be a valid https:// URL');
          setIsReady(true);
          return;
        }
        if (!safeLaunch) {
          setError('Invalid EHR launch: launch token is missing or empty');
          setIsReady(true);
          return;
        }

        setIss(safeIss);
        setLaunch(safeLaunch);
        setLaunchMode('ehr');
        setError(null);
        setIsReady(true);
        return;
      }

      // Post-auth phase: extract patient ID from OAuth callback redirect
      const patientParam = searchParams.get('patient') || searchParams.get('patient_id');

      if (!patientParam) {
        setError('Missing patient parameter in URL. Expected format: ?patient=<patient-id> or ?patient_id=<patient-id>');
        setIsReady(true);
        return;
      }

      const trimmedPatientId = patientParam.trim();

      if (trimmedPatientId.length === 0) {
        setError('Invalid patient ID: cannot be empty');
        setIsReady(true);
        return;
      }

      setPatientId(trimmedPatientId);
      setLaunchMode('patient');
      setError(null);
      setIsReady(true);

    } catch {
      setError('Failed to parse launch context from URL');
      setIsReady(true);
    }
  }, [searchParams]);

  return {
    patientId,
    iss,
    launch,
    launchMode,
    isReady,
    error,
  };
};

export default useLaunchContext;
