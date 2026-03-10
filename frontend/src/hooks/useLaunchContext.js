/**
 * SMART on FHIR Launch Context Hook
 * Extracts patient_id from URL parameters to simulate SMART app launch
 */

import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';

export const useLaunchContext = () => {
  const [searchParams] = useSearchParams();
  const [patientId, setPatientId] = useState(null);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    try {
      // Extract patient ID from URL query parameters
      const patientParam = searchParams.get('patient') || searchParams.get('patient_id');
      
      if (!patientParam) {
        setError('Missing patient parameter in URL. Expected format: ?patient=<patient-id> or ?patient_id=<patient-id>');
        setIsReady(true);
        return;
      }

      // Validate patient ID format
      const trimmedPatientId = patientParam.trim();
      
      if (trimmedPatientId.length === 0) {
        setError('Invalid patient ID: cannot be empty');
        setIsReady(true);
        return;
      }

      // Set patient ID and mark as ready
      setPatientId(trimmedPatientId);
      setError(null);
      setIsReady(true);

      console.log('[SMART Launch Context] Patient ID extracted:', trimmedPatientId);

    } catch (err) {
      console.error('[SMART Launch Context] Error parsing URL:', err);
      setError('Failed to parse launch context from URL');
      setIsReady(true);
    }
  }, [searchParams]);

  return {
    patientId,
    isReady,
    error,
  };
};

export default useLaunchContext;
