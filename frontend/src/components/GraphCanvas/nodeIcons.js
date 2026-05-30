/** SVG icons as data URLs for Cytoscape node backgrounds (white glyphs). */

function svgDataUrl(paths, viewBox = "0 0 24 24") {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${paths}</svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

const ICON_PATHS = {
  Patient: `<circle cx="12" cy="8" r="4"/><path d="M6 21v-1a6 6 0 0 1 12 0v1"/>`,
  Observation: `<path d="M3 3v18h18"/><path d="M7 16l4-8 4 5 4-9"/>`,
  Condition: `<path d="M12 21s-6-4.35-6-10a4 4 0 0 1 7-2.5A4 4 0 0 1 18 11c0 5.65-6 10-6 10z"/>`,
  Encounter: `<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>`,
  AllergyIntolerance: `<path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>`,
  Concept: `<path d="M12 2a7 7 0 0 0-4 12.7V17a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-2.3A7 7 0 0 0 12 2z"/><path d="M9 21h6"/>`,
  PatientGroup: `<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>`,
  Gender: `<circle cx="12" cy="8" r="5"/><path d="M12 13v8"/><path d="M9 18h6"/>`,
  Region: `<path d="M12 21s6-5.33 6-10a6 6 0 1 0-12 0c0 4.67 6 10 6 10z"/><circle cx="12" cy="11" r="2"/>`,
  ClinicalCategory: `<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>`,
};

export const NODE_ICON_URLS = Object.fromEntries(
  Object.entries(ICON_PATHS).map(([type, paths]) => [type, svgDataUrl(paths)])
);

export const NODE_TYPES_WITH_ICONS = Object.keys(NODE_ICON_URLS);

const ICON_STYLE = {
  "background-fit": "contain",
  "background-clip": "node",
  "background-opacity": 1,
};

export function iconStyleForType(type, size = "medium") {
  const url = NODE_ICON_URLS[type];
  if (!url) return {};
  const pct = size === "small" ? "72%" : size === "large" ? "50%" : "58%";
  return {
    ...ICON_STYLE,
    "background-image": url,
    "background-width": pct,
    "background-height": pct,
  };
}
