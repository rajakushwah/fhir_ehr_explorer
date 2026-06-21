/** Cytoscape styles — Neo4j Browser–inspired graph look. */

import { NODE_DEFAULT_COLOR, NODE_LABEL_COLOR, NODE_TYPE_COLORS } from "./nodeColors";

const THEMES = {
  dark: {
    edgeColor: "#9AA3AD",
    edgeLabelColor: "#8A9199",
    arrowColor: "#9AA3AD",
    loadingBg: "#4A5568",
    selectBorder: "#68BDF6",
  },
  light: {
    edgeColor: "#BABABA",
    edgeLabelColor: "#888888",
    arrowColor: "#BABABA",
    loadingBg: "#CBD5E1",
    selectBorder: "#4C8EDA",
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
    "font-weight": 500,
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
        "transition-property": "opacity, width, height",
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
        "font-weight": 600,
        "border-width": 0,
        "overlay-color": t.selectBorder,
        "overlay-opacity": 0.15,
        "overlay-padding": 5,
        "z-index": 999,
      },
    },
    {
      selector: "node.expandable",
      style: {
        "overlay-opacity": 0,
      },
    },
    {
      selector: "node.expanded",
      style: {
        "border-width": 0,
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
        width: 1,
        "line-color": t.edgeColor,
        "target-arrow-color": t.arrowColor,
        "target-arrow-shape": "triangle",
        "arrow-scale": 0.55,
        "curve-style": "bezier",
        opacity: 0.9,
        label: "data(relType)",
        "font-size": 6,
        "font-weight": 400,
        "font-family": "Inter, system-ui, sans-serif",
        color: t.edgeLabelColor,
        "text-rotation": "autorotate",
        "text-margin-y": -8,
        "text-background-opacity": 1,
        "text-background-color": theme === "light" ? "#f5f6f8" : "#1a2332",
        "text-background-padding": 2,
        "text-border-opacity": 0,
      },
    },
    {
      selector: "edge.highlighted",
      style: {
        width: 1,
        "line-color": t.edgeColor,
        "target-arrow-color": t.arrowColor,
        color: t.edgeLabelColor,
        opacity: 1,
        "font-size": 6,
        "font-weight": 400,
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
    {
      selector: "node.analytics-concept",
      style: {
        width: "data(nodeSize)",
        height: "data(nodeSize)",
        "background-color": "data(communityColor)",
        "font-size": 9,
        "text-max-width": 72,
      },
    },
    {
      selector: "node.analytics-bridge",
      style: {
        "border-width": 0,
      },
    },
    {
      selector: "node.analytics-anchor",
      style: {
        width: "data(nodeSize)",
        height: "data(nodeSize)",
        "border-width": 0,
      },
    },
    {
      selector: "node.analytics-similar",
      style: {
        width: "data(nodeSize)",
        height: "data(nodeSize)",
      },
    },
    {
      selector: "edge[relType = 'CO_OCCURS']",
      style: {
        width: "data(edgeWidth)",
        label: "data(label)",
        "font-size": 7,
        opacity: 0.75,
      },
    },
    {
      selector: "edge[relType = 'SIMILAR_TO']",
      style: {
        width: 1,
        label: "data(label)",
        "line-style": "dashed",
        "font-size": 6,
        opacity: 0.85,
      },
    },
    {
      selector: "node.concept-drill-center",
      style: {
        width: 88,
        height: 88,
        "font-size": 10,
        "text-max-width": 78,
        "border-width": 0,
      },
    },
    {
      selector: "node.concept-drill-with",
      style: {
        width: 62,
        height: 62,
        opacity: 1,
        "border-width": 0,
      },
    },
    {
      selector: "node.concept-drill-with.expandable, node.concept-drill-without.expandable",
      style: {
        "overlay-opacity": 0,
      },
    },
    {
      selector: "node.concept-drill-with.concept-drill-picked",
      style: {
        width: 68,
        height: 68,
        "border-width": 0,
        "overlay-color": "#059669",
        "overlay-opacity": 0.2,
        "overlay-padding": 5,
        "z-index": 999,
      },
    },
    {
      selector: "node.concept-drill-without.concept-drill-picked",
      style: {
        width: 58,
        height: 58,
        opacity: 1,
        "border-width": 0,
        "overlay-color": "#64748b",
        "overlay-opacity": 0.18,
        "overlay-padding": 5,
        "z-index": 999,
      },
    },
    {
      selector: "node.concept-drill-without",
      style: {
        width: 54,
        height: 54,
        opacity: 0.28,
      },
    },
    {
      selector: "edge.concept-drill-active",
      style: {
        width: 1,
        "line-color": t.edgeColor,
        "target-arrow-color": t.arrowColor,
        color: t.edgeLabelColor,
        opacity: 0.9,
      },
    },
    {
      selector: "node.concept-drill-summary",
      style: {
        width: 72,
        height: 72,
        "font-size": 9,
        "text-max-width": 68,
        "border-width": 0,
        opacity: 0.7,
        "background-color": "#C8CED6",
        color: NODE_LABEL_COLOR,
      },
    },
    {
      selector: "edge.concept-drill-summary-edge",
      style: {
        width: 1,
        "line-color": "#BABABA",
        "line-style": "dashed",
        "target-arrow-color": "#BABABA",
        opacity: 0.55,
      },
    },
  ];
}

/** @deprecated use getCytoscapeStyles */
export const cytoscapeStyles = getCytoscapeStyles("dark");
