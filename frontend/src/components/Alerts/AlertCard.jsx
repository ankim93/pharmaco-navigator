/**
 * Clinical Alert Card Component
 * Displays individual drug-gene interaction alerts with Traffic Light color coding
 */

import React, { useState } from 'react';
import { 
  AlertTriangle, 
  AlertCircle, 
  CheckCircle, 
  HelpCircle,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Dna,
  Tablets
} from 'lucide-react';

const ALERT_STYLES = {
  RED: {
    bg: 'bg-white',
    border: 'border-gray-200',
    accentBorder: 'border-l-rose-700',
    headerBg: 'bg-rose-200',
    icon: AlertTriangle,
    iconColor: 'text-rose-700',
    textColor: 'text-rose-900',
    badgeColor: 'bg-rose-100 text-rose-800',
  },
  YELLOW: {
    bg: 'bg-white',
    border: 'border-gray-200',
    accentBorder: 'border-l-yellow-400',
    headerBg: 'bg-yellow-100',
    icon: AlertCircle,
    iconColor: 'text-amber-700',
    textColor: 'text-amber-900',
    badgeColor: 'bg-amber-100 text-amber-800',
  },
  GREEN: {
    bg: 'bg-white',
    border: 'border-gray-200',
    accentBorder: 'border-l-emerald-600',
    headerBg: 'bg-emerald-200',
    icon: CheckCircle,
    iconColor: 'text-emerald-700',
    textColor: 'text-emerald-900',
    badgeColor: 'bg-emerald-100 text-emerald-800',
  },
  GREY: {
    bg: 'bg-white',
    border: 'border-gray-200',
    accentBorder: 'border-l-slate-500',
    headerBg: 'bg-gray-200',
    icon: HelpCircle,
    iconColor: 'text-gray-600',
    textColor: 'text-gray-900',
    badgeColor: 'bg-gray-100 text-gray-800',
  },
};

export const AlertCard = ({ alert }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const style = ALERT_STYLES[alert.alert_color] || ALERT_STYLES.GREY;
  const Icon = style.icon;

  return (
    <div 
      className={`${style.bg} border ${style.border} border-l-4 ${style.accentBorder} rounded-lg shadow-md 
                  hover:shadow-lg transition-shadow duration-200`}
    >
      {/* Card Header */}
      <div className={`${style.headerBg} px-4 py-3 rounded-t-md flex items-center justify-between`}>
        <div className="flex items-center space-x-3">
          <Icon className={`h-5 w-5 ${style.iconColor}`} />
          <h3 className={`${style.textColor} font-semibold text-lg`}>
            {alert.drug_name}
          </h3>
        </div>
        <span className={`${style.badgeColor} text-xs font-semibold px-2 py-1 rounded`}>
          {alert.alert_color}
        </span>
      </div>

      {/* Card Body */}
      <div className="p-4">
        {/* Gene and Phenotype Info */}
        <div className="flex items-center space-x-4 mb-3">
          <div className="flex items-center space-x-2">
            <Dna className={`h-4 w-4 ${style.textColor}`} />
            <span className={`text-sm font-semibold ${style.textColor}`}>
              {alert.gene_symbol}
            </span>
          </div>
          <div className={`${style.badgeColor} px-3 py-1 rounded-full text-xs font-medium`}>
            {alert.phenotype}
          </div>
        </div>

        {/* Clinical Action */}
        <div className={`${style.textColor} text-sm leading-relaxed mb-3`}>
          <p className="font-medium">Clinical Recommendation:</p>
          <p className="mt-1">{alert.clinical_action}</p>
        </div>

        {/* Evidence Level Badge */}
        <div className="flex items-center space-x-2 mb-3">
          <span className={`text-xs ${style.textColor} font-semibold`}>
            Evidence:
          </span>
          <span className={`${style.badgeColor} px-2 py-0.5 rounded text-xs font-medium`}>
            {alert.classification} | Level {alert.guideline_level}
          </span>
        </div>

        {/* Expandable Details Section */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className={`w-full flex items-center justify-between text-sm ${style.textColor} 
                     font-medium py-2 px-3 rounded hover:bg-white hover:bg-opacity-30 
                     transition-colors`}
        >
          <span>View CPIC Guideline</span>
          {isExpanded ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </button>

        {/* Affected medications */}
        {alert.alert_color === 'GREY' && alert.affected_medications && alert.affected_medications.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            <p className="text-xs font-semibold text-gray-600 mb-2 flex items-center gap-1">
              <Tablets className="h-3 w-3" />
              Affected Active Medications:
            </p>
            <div className="flex flex-wrap gap-1">
              {alert.affected_medications.map((med) => (
                <span
                  key={med}
                  className="bg-gray-200 text-gray-800 text-xs font-medium px-2 py-0.5 rounded-full border border-gray-300"
                >
                  {med}
                </span>
              ))}
            </div>
          </div>
        )}

        {isExpanded && (
          <div className="mt-2 pt-2 border-t border-gray-300">
            <a
              href={alert.guideline_url}
              target="_blank"
              rel="noopener noreferrer"
              className={`inline-flex items-center space-x-2 ${style.textColor} 
                         hover:underline text-sm`}
            >
              <ExternalLink className="h-4 w-4" />
              <span>Open Full CPIC Guideline</span>
            </a>
          </div>
        )}
      </div>
    </div>
  );
};

export default AlertCard;
