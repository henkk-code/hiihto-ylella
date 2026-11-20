# CLAUDE.md

## UI & UX Design Rules (Strict)
- Design System: Follow [IBM Carbon / GitHub Primer] principles—high information density, utilitarian clarity, and zero decorative fluff.
- Layout & Structure: Avoid "card soup." Do not wrap every section in shadowed cards. Use a strict 12-column CSS grid with 1px hairline borders (border-neutral-200 / border-neutral-800) to divide regions.
- Typography: Use IBM Plex Sans for UI copy and IBM Plex Mono with tabular-nums for all metrics, dates, IDs, and data tables.
- Color Palette: No purple, indigo, or blue-to-violet gradients. Use a monochromatic slate base (#FAFAFA light / #0D0E11 dark) with a single functional accent (#D9480F burnt orange) reserved strictly for primary actions and active states.
- Geometry & Depth: Maximum border-radius of 2px (rounded-xs). No drop shadows (shadow-none); establish depth purely through surface lightness steps and 1px borders.
- Navigation & UX: Prioritize keyboard-first navigation, compact data tables, and persistent sidebars over marketing-style hero sections or oversized padding.
