/**
 * Error Alert Component
 * Displays error messages with appropriate styling and retry action
 */

import React from 'react';
import { AlertTriangle, RefreshCw, WifiOff } from 'lucide-react';

export const ErrorAlert = ({ 
  error, 
  onRetry, 
  type = 'error' 
}) => {
  const isConnectionError = error?.message?.toLowerCase().includes('network') ||
                           error?.message?.toLowerCase().includes('connect');

  const Icon = isConnectionError ? WifiOff : AlertTriangle;
  
  const title = isConnectionError 
    ? 'Backend Connection Error'
    : 'Unable to Load Clinical Data';

  return (
    <div className="flex items-center justify-center min-h-[400px] px-4">
      <div className="max-w-md w-full bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0">
            <Icon className="h-6 w-6 text-red-600" />
          </div>
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-red-900 mb-1">
              {title}
            </h3>
            <p className="text-sm text-red-700 mb-4">
              {error?.message || 'An unexpected error occurred'}
            </p>
            
            {isConnectionError && (
              <p className="text-xs text-red-600 mb-4">
                Please ensure the backend server is running at{' '}
                <code className="bg-red-100 px-1 py-0.5 rounded">
                  http://localhost:8000
                </code>
              </p>
            )}

            {onRetry && (
              <button
                onClick={onRetry}
                className="inline-flex items-center px-4 py-2 bg-red-600 hover:bg-red-700 
                           text-white text-sm font-medium rounded-md transition-colors
                           focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry Connection
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ErrorAlert;
