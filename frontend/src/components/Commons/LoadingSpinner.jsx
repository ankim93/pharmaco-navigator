/**
 * Loading Spinner Component
 * Displays a centered loading spinner with optional message
 */

import React from 'react';
import { Loader2 } from 'lucide-react';

export const LoadingSpinner = ({ message = 'Loading clinical data...', size = 'large' }) => {
  const sizeClasses = {
    small: 'h-5 w-5',
    medium: 'h-8 w-8',
    large: 'h-12 w-12',
  };

  const iconSize = sizeClasses[size] || sizeClasses.large;

  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
      <Loader2 className={`${iconSize} animate-spin text-blue-600`} />
      <p className="text-gray-600 text-sm font-medium">{message}</p>
    </div>
  );
};

export default LoadingSpinner;
