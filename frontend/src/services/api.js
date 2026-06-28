/**
 * API Service Layer for Pharmaco-Navigator Backend
 * Handles all HTTP communication with the FastAPI backend
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Enable session cookies for SMART on FHIR authentication
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNABORTED') {
      throw new Error('Request timeout - backend server not responding');
    }
    
    if (error.code === 'ERR_NETWORK') {
      throw new Error('Network error - unable to connect to backend server');
    }
    
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response;
      
      if (status === 404) {
        throw new Error(data.detail || 'Patient data not found');
      }
      
      if (status === 503) {
        throw new Error('Backend service temporarily unavailable');
      }
      
      if (status === 401 || status === 403) {
        throw new Error('Authentication required or access denied');
      }
      
      throw new Error(data.detail || `Server error (${status})`);
    }
    
    throw error;
  }
);

/**
 * Fetch Clinical Decision Support alerts for a patient
 * @param {string} patientId - Patient identifier from SMART launch context
 * @returns {Promise<Object>} Clinical alert response with red/yellow/green/grey alerts
 */
export const fetchPatientAlerts = async (patientId) => {
  if (!patientId) {
    throw new Error('Patient ID is required');
  }
  const response = await apiClient.get(`/patient/${patientId}/alerts`);
  return response.data;
};

/**
 * Health check endpoint to verify backend availability
 * @returns {Promise<Object>} Health status
 */
export const checkBackendHealth = async () => {
  const response = await apiClient.get('/health');
  return response.data;
};

export default {
  fetchPatientAlerts,
  checkBackendHealth,
};
