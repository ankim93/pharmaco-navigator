/**
 * Dashboard Header Component
 * Displays patient information and metabolic status for key pharmacogenes
 */

import React from 'react';
import { 
  User, 
  Dna,
  Info,
  FlaskConical,
} from 'lucide-react';
import { PharmacoIcon } from '../Commons/PharmacoIcon';

const GENE_DESCRIPTIONS = {
  CYP2D6: 'Codeine, Tramadol, SSRIs',
  CYP2C19: 'Clopidogrel, PPIs, SSRIs',
  SLCO1B1: 'Statins (Simvastatin)',
  ABCB1: 'Tacrolimus, Digoxin',
};



const getPhenotypeColor = (phenotype) => {
  if (!phenotype || phenotype.includes('Missing') || phenotype.includes('Unknown')) {
    return 'bg-gray-100 text-gray-700 border-gray-300';
  }
  const lower = phenotype.toLowerCase();
  if (lower.includes('poor')) return 'bg-rose-100 text-rose-800 border-rose-300';
  if (lower.includes('intermediate') || lower.includes('decreased')) return 'bg-amber-100 text-amber-800 border-amber-300';
  if (lower.includes('normal') || lower.includes('rapid') || lower.includes('increased')) return 'bg-emerald-100 text-emerald-800 border-emerald-300';
  return 'bg-gray-100 text-gray-700 border-gray-300';
};

/**
 * Shows gene name, phenotype badge, medication descriptions,
 * and a row of colored alert-count pills (RED / YELLOW / GREEN).
 */
const GeneStatusBadge = ({ gene, geneData }) => {
  const phenotype = geneData?.phenotype || null;
  // hasGuidelines === false — force grey regardless of phenotype value.
  const colorClass = geneData?.hasGuidelines === false
    ? 'bg-gray-100 text-gray-700 border-gray-300'
    : getPhenotypeColor(phenotype);
  const displayPhenotype = phenotype || 'Data Missing';
  const red    = geneData?.red    ?? 0;
  const yellow = geneData?.yellow ?? 0;
  const green  = geneData?.green  ?? 0;
  const hasAlerts = (red + yellow + green) > 0;

  return (
    <div className="flex flex-col space-y-2">
      {/* Gene name */}
      <div className="flex items-center space-x-2">
        <Dna className="h-4 w-4 text-white" />
        <span className="text-lg font-bold text-white">{gene}</span>
      </div>

      {/* Phenotype badge */}
      <div className={`${colorClass} border px-3 py-1 rounded-md text-xs font-medium text-center`}>
        {displayPhenotype}
      </div>

      {/* Alert count pills */}
      {hasAlerts ? (
        <div className="flex items-center justify-center gap-1">
          {red > 0 && (
            <span className="bg-rose-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
              {red}
            </span>
          )}
          {yellow > 0 && (
            <span className="bg-amber-400 text-white text-xs font-bold px-2 py-0.5 rounded-full">
              {yellow}
            </span>
          )}
          {green > 0 && (
            <span className="bg-emerald-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
              {green}
            </span>
          )}
        </div>
      ) : (
        <p className="text-xs text-blue-200 text-center italic">no active med alerts</p>
      )}

      {/* Gene–drug summary */}
      <p className="text-xs text-blue-100 text-center">{GENE_DESCRIPTIONS[gene]}</p>
    </div>
  );
};

export const DashboardHeader = ({ patientId, geneSummary, totalMedications }) => {
  const summary = geneSummary || {};

  return (
    <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-lg shadow-lg p-6 mb-6">
      {/* Header Title */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <PharmacoIcon className="h-8 w-8" />
          <div>
            <h1 className="text-2xl font-bold">Pharmaco-Navigator</h1>
            <p className="text-blue-100 text-sm">Clinical Decision Support System</p>
          </div>
        </div>
        <div className="text-right">
          <div className="flex items-center space-x-2 justify-end mb-1">
            <User className="h-5 w-5" />
            <span className="text-sm font-medium">Patient ID:</span>
          </div>
          <p className="text-lg font-bold">{patientId}</p>
        </div>
      </div>

      {/* Genomic Profile Summary */}
      <div className="bg-white bg-opacity-10 rounded-lg p-4 backdrop-blur-sm">
        <div className="flex items-center space-x-2 mb-4">
          <FlaskConical className="h-5 w-5" />
          <h2 className="text-lg font-semibold">Pharmacogenomic Profile</h2>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <GeneStatusBadge gene="CYP2D6"   geneData={summary.CYP2D6}   />
          <GeneStatusBadge gene="CYP2C19"  geneData={summary.CYP2C19}  />
          <GeneStatusBadge gene="SLCO1B1"  geneData={summary.SLCO1B1}  />
          <GeneStatusBadge gene="ABCB1"    geneData={summary.ABCB1}    />
        </div>

        <div className="flex items-start space-x-2 text-xs bg-blue-900 bg-opacity-30 rounded p-3">
          <Info className="h-4 w-4 flex-shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            This dashboard analyzes {totalMedications || 0} medication{totalMedications !== 1 ? 's' : ''}{' '}
            against CPIC (Clinical Pharmacogenomics Implementation Consortium) guidelines
            to provide evidence-based drug-gene interaction alerts.
          </p>
        </div>
      </div>
    </div>
  );
};

export default DashboardHeader;
