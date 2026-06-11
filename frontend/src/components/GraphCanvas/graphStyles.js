/** Cytoscape styles — circular nodes, no borders. */

import { NODE_DEFAULT_COLOR, NODE_LABEL_COLOR, NODE_TYPE_COLORS } from "./nodeColors";

const THEMES = {
  dark: {
    edgeColor: "#334155",
    edgeLabelColor: "#94a3b8",
    arrowColor: "#475569",
    loadingBg: "#E8ECF0",
    highlightEdge: "#5b8fd4",
    selectOverlay: "#d946a8",
    expandableOverlay: "rgba(32, 63, 104, 0.35)",
  },
  light: {
    edgeColor: "#94a3b8",
    edgeLabelColor: "#64748b",
    arrowColor: "#64748b",
    loadingBg: "#E8ECF0",
    highlightEdge: "#203f68",
    selectOverlay: "#d946a8",
    expandableOverlay: "rgba(32, 63, 104, 0.25)",
  },
};

function typedNode(type, diameter = 44, textStyle = {}) {
  const fill = NODE_TYPE_COLORS[type] ?? NODE_DEFAULT_COLOR;
  return {
    selector: `node[type = '${type}']`,
    style: {
      "background-image": "none",
      "background-opacity": 1,
      "background-color": fill,
      shape: "ellipse",
      width: diameter,
      height: diameter,
      "border-width": 0,
      ...textStyle,
    },
  };
}

export function getCytoscapeStyles(theme = "dark") {
  const t = THEMES[theme] ?? THEMES.dark;

  const labelInside = {
    label: "data(shortLabel)",
    "font-family": "Inter, system-ui, sans-serif",
    "font-weight": 400,
    color: NODE_LABEL_COLOR,
    "text-outline-width": 0,
    "text-valign": "center",
    "text-halign": "center",
    "text-margin-y": 0,
    "text-wrap": "ellipsis",
    "text-overflow-wrap": "anywhere",
  };

  return [
    {
      selector: "node",
      style: {
        ...labelInside,
        width: 44,
        height: 44,
        shape: "ellipse",
        "background-color": NODE_DEFAULT_COLOR,
        "background-image": "none",
        "background-opacity": 1,
        "border-width": 0,
        "font-size": 8,
        "text-max-width": 40,
        "overlay-opacity": 0,
        "transition-property": "opacity, width, height, overlay-opacity",
        "transition-duration": 180,
      },
    },
    typedNode("Concept", 72, { "font-size": 9, "text-max-width": 62 }),
    typedNode("PatientGroup", 72, { "font-size": 9, "text-max-width": 64 }),
    typedNode(
      "Gender",
      58,
      { "font-size": 8, "text-max-width": 52, "text-wrap": "wrap", "line-height": 1.1 }
    ),
    typedNode(
      "Region",
      58,
      { "font-size": 8, "text-max-width": 52, "text-wrap": "wrap", "line-height": 1.1 }
    ),
    typedNode("Patient", 56, { "font-size": 9, "text-max-width": 48 }),
    typedNode("ClinicalCategory", 64, { "font-size": 8, "text-max-width": 56 }),
    typedNode("Condition", 44, { "font-size": 7, "text-max-width": 38 }),
    typedNode("Observation", 44, { "font-size": 7, "text-max-width": 38 }),
    typedNode("AllergyIntolerance", 44, { "font-size": 7, "text-max-width": 38 }),
    typedNode("Encounter", 48, { "font-size": 7, "text-max-width": 42 }),
    typedNode("Procedure", 44, { "font-size": 7, "text-max-width": 38 }),
    typedNode("MedicationRequest", 44, { "font-size": 7, "text-max-width": 38 }),
    typedNode("Immunization", 44, { "font-size": 7, "text-max-width": 38 }),
    typedNode("DiagnosticReport", 44, { "font-size": 7, "text-max-width": 38 }),
    typedNode("Organization", 44, { "font-size": 7, "text-max-width": 38 }),
    typedNode("Location", 44, { "font-size": 7, "text-max-width": 38 }),
    typedNode("Practitioner", 44, { "font-size": 7, "text-max-width": 38 }),
    {
      selector: "node:selected",
      style: {
        "font-weight": 500,
        "overlay-color": t.selectOverlay,
        "overlay-opacity": 0.2,
        "overlay-padding": 6,
        "z-index": 999,
      },
    },
    {
      selector: "node.expandable",
      style: {
        "overlay-color": t.expandableOverlay,
        "overlay-opacity": 0.12,
        "overlay-padding": 4,
      },
    },
    {
      selector: "node.expanded",
      style: {
        "overlay-opacity": 0,
      },
    },
    {
      selector: "node.loading",
      style: {
        "background-color": t.loadingBg,
        "background-image": "none",
        "overlay-opacity": 0,
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
        label: "data(relType)",
        "font-size": 6,
        "font-weight": 400,
        "font-family": "Inter, system-ui, sans-serif",
        color: t.edgeLabelColor,
        "text-rotation": "autorotate",
        "text-margin-y": -10,
        "text-background-opacity": 0.85,
        "text-background-color": theme === "light" ? "#ffffff" : "#162033",
        "text-background-padding": 2,
        "text-border-opacity": 0,
      },
    },
    {
      selector: "edge.highlighted",
      style: {
        width: 2,
        "line-color": t.highlightEdge,
        "target-arrow-color": t.highlightEdge,
        color: t.highlightEdge,
        opacity: 0.95,
        "font-size": 8,
        "font-weight": 500,
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
