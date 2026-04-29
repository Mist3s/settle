/**
 * Chart color palette — hardcoded hex values for Recharts SVG compatibility.
 *
 * SVG `fill` / `stroke` attributes don't reliably resolve CSS custom properties
 * (e.g., `hsl(var(--primary))`) or oklch() in all browsers. We use hex colors
 * derived from the Settle brand palette defined in index.css.
 *
 * Each color has a semantic name matching its role in the design system.
 */

// Brand primary — indigo/blue
export const PRIMARY = "#4338ca";

// Semantic colors
export const SUCCESS = "#22c55e";
export const WARNING = "#eab308";
export const DANGER = "#ef4444";

// Extended chart palette — for pie charts and multi-series data
export const CHART_PALETTE = [
  PRIMARY,           // indigo
  SUCCESS,           // green
  WARNING,           // amber/yellow
  DANGER,            // red
  "#8b5cf6",         // violet
  "#0ea5e9",         // sky blue
  "#ec4899",         // pink
  "#14b8a6",         // teal
  "#f97316",         // orange
  "#6366f1",         // indigo light
] as const;

// Specific bar/area chart colors
export const CHART = {
  principal: PRIMARY,
  interest: WARNING,
  installment: "#8b5cf6",  // violet
  balance: "#0ea5e9",      // sky blue
  forecast: PRIMARY,
  forecastDimmed: "#a5b4fc",
  deficit: DANGER,

  // Comparison view (simulator)
  current: PRIMARY,
  scenario: SUCCESS,
} as const;
