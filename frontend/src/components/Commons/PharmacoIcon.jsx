/**
 * PharmacoIcon for Pharmaco-Navigator.
 */

export const PharmacoIcon = ({ className = 'h-8 w-8' }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    aria-label="Pharmaco-Navigator"
    role="img"
  >
    {/* Bottle cap */}
    <rect x="6" y="2" width="12" height="4" rx="1.5" />

    {/* Bottle body */}
    <rect x="7" y="6" width="10" height="16" rx="2" />

    {/* DNA strand 1 — sinusoidal S-curves (left→right→left→right) */}
    <path d="M9 8 C9 9.4 15 10.6 15 12 C15 13.4 9 14.6 9 16 C9 17.4 15 18.6 15 20" strokeWidth="1.5" />

    {/* DNA strand 2 — opposite phase (right→left→right→left) */}
    <path d="M15 8 C15 9.4 9 10.6 9 12 C9 13.4 15 14.6 15 16 C15 17.4 9 18.6 9 20" strokeWidth="1.5" />

    {/* Helix rungs at strand extremes */}
    <line x1="9" y1="8" x2="15" y2="8" strokeWidth="1" />
    <line x1="9" y1="12" x2="15" y2="12" strokeWidth="1" />
    <line x1="9" y1="16" x2="15" y2="16" strokeWidth="1" />
    <line x1="9" y1="20" x2="15" y2="20" strokeWidth="1" />
  </svg>
);

export default PharmacoIcon;
