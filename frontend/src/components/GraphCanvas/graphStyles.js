/** Cytoscape styles — light solid-color nodes, labels clipped inside. */

import { NODE_LABEL_COLOR, NODE_TYPE_COLORS, nodeBorderColor } from "./nodeColors";

const THEMES = {
  dark: {
    border: "rgba(32, 63, 104, 0.2)",
    edgeColor: "#334155",
    edgeLabelColor: "#94a3b8",
    arrowColor: "#475569",
    expandableBorder: "rgba(32, 63, 104, 0.45)",
    expandedBorder: "#475569",
    loadingBg: "#cbd5e1",
    highlightEdge: "#5b8fd4",
    selectBorder: "#d946a8",
  },
  light: {
    border: "rgba(32, 63, 104, 0.2)",
    edgeColor: "#94a3b8",
    edgeLabelColor: "#64748b",
    arrowColor: "#64748b",
    expandableBorder: "rgba(32, 63, 104, 0.45)",
    expandedBorder: "#94a3b8",
    loadingBg: "#cbd5e1",
    highlightEdge: "#203f68",
    selectBorder: "#d946a8",
  },
};

function typedNode(type, size = {}, textStyle = {}, shape = "ellipse") {
  const fill = NODE_TYPE_COLORS[type] ?? "#C7B8F5";
  return {
    selector: `node[type = '${type}']`,
    style: {
      "background-image": "none",
      "background-opacity": 1,
      "background-color": fill,
      "border-color": nodeBorderColor(type),
      shape,
      width: 44,
      height: 44,
      ...size,
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
        label: "",
        width: 44,
        height: 44,
        shape: "ellipse",
        "background-color": "#C7B8F5",
        "background-image": "none",
        "background-opacity": 1,
        "border-width": 1,
        "border-color": t.border,
        "border-opacity": 1,
        "transition-property": "opacity, border-width, width, height",
        "transition-duration": 180,
      },
    },
    typedNode("Concept", { width: 72, height: 72 }, { "font-size": 9, "text-max-width": 62 }),
    typedNode(
      "PatientGroup",
      { width: 72, height: 48 },
      { "font-size": 9, "text-max-width": 64 },
      "round-rectangle"
    ),
    typedNode("Gender", { width: 44, height: 44 }, { "font-size": 8, "text-max-width": 38 }),
    typedNode("Region", { width: 44, height: 44 }, { "font-size": 8, "text-max-width": 38 }),
    typedNode("Patient", { width: 56, height: 56 }, { "font-size": 9, "text-max-width": 48 }),
    typedNode(
      "ClinicalCategory",
      { width: 80, height: 48 },
      { "font-size": 8, "text-max-width": 72 },
      "round-rectangle"
    ),
    typedNode("Condition", { width: 44, height: 44 }, { "font-size": 7, "text-max-width": 38 }),
    typedNode("Observation", { width: 44, height: 44 }, { "font-size": 7, "text-max-width": 38 }),
    typedNode("AllergyIntolerance", { width: 44, height: 44 }, { "font-size": 7, "text-max-width": 38 }),
    typedNode(
      "Encounter",
      { width: 48, height: 48 },
      { "font-size": 7, "text-max-width": 42 },
      "round-rectangle"
    ),
    typedNode("Procedure", { width: 44, height: 44 }, { "font-size": 7, "text-max-width": 38 }),
    typedNode("MedicationRequest", { width: 44, height: 44 }, { "font-size": 7, "text-max-width": 38 }),
    typedNode("Immunization", { width: 44, height: 44 }, { "font-size": 7, "text-max-width": 38 }),
    typedNode("DiagnosticReport", { width: 44, height: 44 }, { "font-size": 7, "text-max-width": 38 }),
    typedNode("Organization", { width: 44, height: 44 }, { "font-size": 7, "text-max-width": 38 }),
    typedNode("Location", { width: 44, height: 44 }, { "font-size": 7, "text-max-width": 38 }),
    typedNode("Practitioner", { width: 44, height: 44 }, { "font-size": 7, "text-max-width": 38 }),
    {
      selector:
        "node.show-label, node:selected, node[type = 'ClinicalCategory'], node[type = 'Patient'], node[type = 'Concept'], node[type = 'PatientGroup']",
      style: labelInside,
    },
    {
      selector: "node.expandable",
      style: {
        "border-width": 1,
        "border-color": t.expandableBorder,
        "border-opacity": 1,
      },
    },
    {
      selector: "node.expanded",
      style: {
        "border-color": t.expandedBorder,
        "border-opacity": 0.75,
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
      selector: "node:selected",
      style: {
        "border-width": 1,
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
