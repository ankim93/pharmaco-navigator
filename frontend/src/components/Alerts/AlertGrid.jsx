/**
 * Alert Grid Component
 * Organizes alert cards into a three-column traffic light layout
 */

import React from 'react';
import { AlertCard } from './AlertCard';
import { AlertTriangle, AlertCircle, CheckCircle, HelpCircle } from 'lucide-react';

const AlertSection = ({ title, alerts, color, Icon, emptyMessage }) => (
  <div className="space-y-3">
    <div className="flex items-center space-x-2 mb-4">
      <Icon className={`h-5 w-5 ${color}`} />
      <h2 className="text-lg font-bold text-gray-800">
        {title}
        <span className="ml-2 text-sm font-normal text-gray-600">
          ({alerts.length})
        </span>
      </h2>
    </div>

    {alerts.length === 0 ? (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
        <p className="text-sm text-gray-500">{emptyMessage}</p>
      </div>
    ) : (
      <div className="space-y-3">
        {alerts.map((alert, index) => (
          <AlertCard key={`${alert.drug_name}-${alert.gene_symbol}-${index}`} alert={alert} />
        ))}
      </div>
    )}
  </div>
);

export const AlertGrid = ({ alerts }) => {
  const { red_alerts = [], yellow_alerts = [], green_alerts = [], grey_alerts = [] } = alerts;

  const hasGreyAlerts = grey_alerts.length > 0;

  return (
    <div className={`grid grid-cols-1 gap-6 ${hasGreyAlerts ? 'lg:grid-cols-4' : 'lg:grid-cols-3'}`}>
      {/* RED ALERTS Column */}
      <AlertSection
        title="High Risk"
        alerts={red_alerts}
        color="text-rose-600"
        Icon={AlertTriangle}
        emptyMessage="No high-risk drug interactions detected"
      />

      {/* YELLOW ALERTS Column */}
      <AlertSection
        title="Moderate Risk"
        alerts={yellow_alerts}
        color="text-amber-600"
        Icon={AlertCircle}
        emptyMessage="No moderate-risk interactions detected"
      />

      {/* GREEN ALERTS Column */}
      <AlertSection
        title="Safe / Standard Dosing"
        alerts={green_alerts}
        color="text-emerald-600"
        Icon={CheckCircle}
        emptyMessage="No medications cleared for standard dosing"
      />

      {/* GREY ALERTS Column */}
      {hasGreyAlerts && (
        <AlertSection
          title="Data Missing/Unknown"
          alerts={grey_alerts}
          color="text-gray-500"
          Icon={HelpCircle}
          emptyMessage="No data available for this gene"
        />
      )}
    </div>
  );
};

export default AlertGrid;
