/** Bloom-inspired Cytoscape styles with per-type icons and theme support. */

import { iconStyleForType } from "./nodeIcons";

const THEMES = {
  dark: {
    border: "#334155",
    labelColor: "#e8eef5",
    labelOutline: "#0f1729",
    edgeColor: "#334155",
    arrowColor: "#475569",
    expandableBorder: "#5b8fd4",
    expandedBorder: "#475569",
    loadingBg: "#475569",
    categoryBg: "#203f68",
    categoryBorder: "#d946a8",
    highlightEdge: "#5b8fd4",
    selectBorder: "#d946a8",
  },
  light: {
    border: "#cbd5e1",
    labelColor: "#203f68",
    labelOutline: "#ffffff",
    edgeColor: "#94a3b8",
    arrowColor: "#64748b",
    expandableBorder: "#203f68",
    expandedBorder: "#94a3b8",
    loadingBg: "#cbd5e1",
    categoryBg: "#203f68",
    categoryBorder: "#d946a8",
    highlightEdge: "#203f68",
    selectBorder: "#d946a8",
  },
};

function typedNode(type, colors, size = "medium", extra = {}) {
  return {
    selector: `node[type = '${type}']`,
    style: {
      ...iconStyleForType(type, size),
      ...colors,
      ...extra,
    },
  };
}

export function getCytoscapeStyles(theme = "dark") {
  const t = THEMES[theme] ?? THEMES.dark;

  return [
    {
      selector: "node",
      style: {
        label: "",
        width: 36,
        height: 36,
        "background-opacity": 0.95,
        "border-width": 2,
        "border-color": t.border,
        "border-opacity": 0.85,
        "transition-property": "opacity, border-width, width, height",
        "transition-duration": 180,
      },
    },
    typedNode("Concept", {
      shape: "ellipse",
      width: 56,
      height: 56,
      "background-color": "#ec4899",
      "border-color": "#db2777",
    }, "large"),
    typedNode("PatientGroup", {
      shape: "round-rectangle",
      width: 52,
      height: 40,
      "background-color": "#6366f1",
      "border-color": "#4f46e5",
    }, "medium"),
    typedNode("Gender", {
      "background-color": "#8b5cf6",
      "border-color": "#7c3aed",
    }),
    typedNode("Region", {
      "background-color": "#06b6d4",
      "border-color": "#0891b2",
    }),
    typedNode("Patient", {
      width: 48,
      height: 48,
      "background-color": "#203f68",
      "border-color": "#1a3354",
      "border-width": 3,
    }, "large"),
    typedNode("ClinicalCategory", {
      shape: "round-rectangle",
      width: 64,
      height: 44,
      "background-color": t.categoryBg,
      "border-color": t.categoryBorder,
      "border-width": 3,
    }, "medium"),
    typedNode("Condition", {
      width: 30,
      height: 30,
      "background-color": "#0ea5e9",
      "border-color": "#0284c7",
    }, "small"),
    typedNode("Observation", {
      width: 26,
      height: 26,
      "background-color": "#10b981",
      "border-color": "#059669",
    }, "small"),
    typedNode("AllergyIntolerance", {
      width: 28,
      height: 28,
      "background-color": "#f97316",
      "border-color": "#ea580c",
    }, "small"),
    typedNode("Encounter", {
      width: 32,
      height: 32,
      shape: "round-rectangle",
      "background-color": "#ec4899",
      "border-color": "#db2777",
    }, "small"),
    {
      selector: "node.expandable",
      style: {
        "border-width": 3,
        "border-color": t.expandableBorder,
        "border-opacity": 0.9,
      },
    },
    {
      selector: "node.expanded",
      style: {
        "border-color": t.expandedBorder,
        "border-opacity": 0.65,
      },
    },
    {
      selector: "node.loading",
      style: {
        "background-color": t.loadingBg,
        "border-color": t.expandableBorder,
        "background-image": "none",
      },
    },
    {
      selector: "node.show-label, node:selected, node[type = 'ClinicalCategory'], node[type = 'Patient'], node[type = 'Concept'], node[type = 'PatientGroup']",
      style: {
        label: "data(shortLabel)",
        "font-size": 10,
        "font-family": "Inter, system-ui, sans-serif",
        "font-weight": 600,
        color: t.labelColor,
        "text-outline-width": 2,
        "text-outline-color": t.labelOutline,
        "text-outline-opacity": 0.95,
        "text-wrap": "wrap",
        "text-max-width": 90,
        "text-valign": "bottom",
        "text-halign": "center",
        "text-margin-y": 6,
      },
    },
    {
      selector: "edge",
      style: {
        width: 1.2,
        "line-color": t.edgeColor,
        "target-arrow-color": t.arrowColor,
        "target-arrow-shape": "triangle",
        "arrow-scale": 0.5,
        "curve-style": "bezier",
        opacity: theme === "light" ? 0.55 : 0.45,
      },
    },
    {
      selector: "edge.highlighted",
      style: {
        width: 2,
        "line-color": t.highlightEdge,
        "target-arrow-color": t.highlightEdge,
        opacity: 0.95,
      },
    },
    {
      selector: "node:selected",
      style: {
        "border-width": 4,
        "border-color": t.selectBorder,
        "background-opacity": 1,
        "z-index": 999,
      },
    },
    {
      selector: ".dimmed",
      style: { opacity: theme === "light" ? 0.18 : 0.12 },
    },
    {
      selector: ".highlighted",
      style: { opacity: 1, "z-index": 100 },
    },
  ];
}

/** @deprecated use getCytoscapeStyles */
export const cytoscapeStyles = getCytoscapeStyles("dark");
