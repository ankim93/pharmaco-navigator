/**
 * Main Dashboard Component
 * Orchestrates the Traffic Light Clinical Decision Support dashboard
 */

import React, { useState, useEffect } from 'react';
import { useLaunchContext } from '../../hooks/useLaunchContext';
import { fetchPatientAlerts } from '../../services/api';
import { DashboardHeader } from './DashboardHeader';
import { AlertGrid } from '../Alerts/AlertGrid';
import { LoadingSpinner } from '../Commons/LoadingSpinner';
import { ErrorAlert } from '../Commons/ErrorAlert';
import { Pill } from 'lucide-react';

/**
 * Build per-gene summary: phenotype + alert counts per risk level.
 */
const extractGeneSummary = (alerts) => {
  const summary = {};

  const add = (alert, color) => {
    const g = alert.gene_symbol;
    if (!g) return;
    if (!summary[g]) {
      summary[g] = { phenotype: alert.phenotype, red: 0, yellow: 0, green: 0 };
    }
    // Grey alerts carry the real phenotype even when no active-med alerts exist
    if (alert.phenotype && !summary[g].phenotype) {
      summary[g].phenotype = alert.phenotype;
    }
    if (color === 'red')    summary[g].red++;
    if (color === 'yellow') summary[g].yellow++;
    if (color === 'green')  summary[g].green++;
  };

  (alerts.red_alerts    || []).forEach(a => add(a, 'red'));
  (alerts.yellow_alerts || []).forEach(a => add(a, 'yellow'));
  (alerts.green_alerts  || []).forEach(a => add(a, 'green'));
  // Grey alerts contribute phenotype info and a hasGuidelines flag
  (alerts.grey_alerts   || []).forEach(a => {
    const g = a.gene_symbol;
    if (!g) return;
    if (!summary[g]) summary[g] = { phenotype: a.phenotype, red: 0, yellow: 0, green: 0 };
    else if (!summary[g].phenotype) summary[g].phenotype = a.phenotype;
    if (a.classification === 'No CPIC Level A/B Guidelines') {
      summary[g].hasGuidelines = false;
    }
  });

  return summary;
};

export const Dashboard = () => {
  const { patientId, isReady, error: launchError } = useLaunchContext();
  
  const [alertData, setAlertData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Fetch clinical alerts from backend
   */
  const loadAlerts = async () => {
    if (!patientId) return;

    setLoading(true);
    setError(null);

    try {
      console.log(`[Dashboard] Fetching alerts for patient: ${patientId}`);
      const data = await fetchPatientAlerts(patientId);
      setAlertData(data);
      console.log('[Dashboard] Alerts loaded successfully:', data);
    } catch (err) {
      console.error('[Dashboard] Error loading alerts:', err);
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  // Load alerts when patient ID is available
  useEffect(() => {
    if (isReady && patientId) {
      loadAlerts();
    }
  }, [isReady, patientId]);

  // Handle launch context errors
  if (launchError) {
    return (
      <div className="h-full bg-gray-100 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-amber-50 border border-amber-300 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-amber-900 mb-2">
            SMART Launch Context Error
          </h2>
          <p className="text-sm text-amber-700 mb-4">{launchError}</p>
          <p className="text-xs text-amber-600">
            Please launch the application with a valid patient parameter:
            <br />
            <code className="bg-amber-100 px-2 py-1 rounded mt-2 block">
              ?patient=test-patient-123
            </code>
          </p>
        </div>
      </div>
    );
  }

  // Show loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100">
        <div className="w-full px-6 py-6">
          <LoadingSpinner message="Loading clinical decision support data..." />
        </div>
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className="min-h-screen bg-gray-100">
        <div className="w-full px-6 py-6">
          <ErrorAlert error={error} onRetry={loadAlerts} />
        </div>
      </div>
    );
  }

  // Show dashboard with alerts
  if (alertData) {
    const geneSummary = extractGeneSummary(alertData);
    const activeMeds = alertData.active_medications || [];
    
    return (
      <div className="min-h-screen bg-gray-100 overflow-auto">
        <div className="w-full px-6 py-6">
          <DashboardHeader
            patientId={alertData.patient_id}
            geneSummary={geneSummary}
            totalMedications={alertData.total_medications}
          />

          {/* Active Medications Panel */}
          {activeMeds.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-lg shadow-sm px-5 py-4 mb-6">
              <div className="flex items-center gap-2 mb-3">
                <Pill className="h-4 w-4 text-gray-500" />
                <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                  Active Medications ({activeMeds.length})
                </h2>
              </div>
              <div className="flex flex-wrap gap-2">
                {activeMeds.map((med) => (
                  <span
                    key={med}
                    className="bg-blue-50 text-blue-800 border border-blue-200 text-sm font-medium px-3 py-1 rounded-full"
                  >
                    {med}
                  </span>
                ))}
              </div>
            </div>
          )}

          <AlertGrid alerts={alertData} />

          {/* Footer */}
          <div className="mt-8 text-center text-xs text-gray-500">
            <p>
              Clinical Decision Support System based on CPIC (Clinical Pharmacogenomics Implementation Consortium) Guidelines
            </p>
            <p className="mt-1">
              Last updated: {new Date().toLocaleString()}
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Default loading state
  return (
    <div className="min-h-screen bg-gray-100">
      <div className="w-full px-6 py-6">
        <LoadingSpinner message="Initializing dashboard..." />
      </div>
    </div>
  );
};

export default Dashboard;
