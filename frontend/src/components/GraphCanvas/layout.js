import fcose from "cytoscape-fcose";

let registered = false;

export function registerFcose(cytoscape) {
  if (!registered) {
    cytoscape.use(fcose);
    registered = true;
  }
}

/** Run force-directed layout on a node collection (Bloom-style spread). */
export function runBloomLayout(cy, focusNode = null) {
  const collection = focusNode
    ? focusNode.closedNeighborhood().nodes()
    : cy.nodes();

  if (collection.length < 2) return Promise.resolve();

  const layout = collection.layout({
    name: "fcose",
    animate: true,
    animationDuration: 450,
    animationEasing: "ease-out-cubic",
    randomize: false,
    fit: false,
    padding: 40,
    nodeDimensionsIncludeLabels: true,
    quality: "default",
    nodeRepulsion: focusNode ? 8500 : 12000,
    idealEdgeLength: (edge) => {
      const t = edge.target().data("type");
      if (t === "Observation") return 90;
      if (t === "Condition") return 110;
      return 140;
    },
    gravity: 0.25,
    gravityRange: 3.8,
    nestingFactor: 0.1,
    numIter: 2500,
    tile: true,
    tilingPaddingVertical: 20,
    tilingPaddingHorizontal: 20,
  });

  return new Promise((resolve) => {
    layout.one("layoutstop", resolve);
    layout.run();
  });
}

export function computeChildPositions(parentPos, count, options = {}) {
  const { baseRadius = 180, maxPerRing = 8 } = options;
  if (count === 0) return [];

  const positions = [];
  for (let i = 0; i < count; i++) {
    const angle = (2 * Math.PI * i) / count - Math.PI / 2;
    positions.push({
      x: parentPos.x + baseRadius * Math.cos(angle),
      y: parentPos.y + baseRadius * Math.sin(angle),
    });
  }
  return positions;
}

export function getNodeTypeColor(type) {
  const colors = {
    Concept: "#ec4899",
    PatientGroup: "#6366f1",
    Gender: "#8b5cf6",
    Region: "#06b6d4",
    Patient: "#203f68",
    ClinicalCategory: "#203f68",
    Condition: "#0ea5e9",
    Observation: "#10b981",
    AllergyIntolerance: "#f97316",
    Encounter: "#ec4899",
  };
  return colors[type] ?? "#64748b";
}

export function ensureShortLabel(data) {
  const label = data.label || data.type || "Node";
  const short =
    data.shortLabel ||
    (label.length > 26 ? `${label.slice(0, 24)}…` : label);
  return { ...data, label, shortLabel: short, fullLabel: data.fullLabel || label };
}
