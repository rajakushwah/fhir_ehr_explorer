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

export { getNodeTypeColor } from "./nodeColors";

const LABEL_LIMITS = {
  Observation: 10,
  Condition: 12,
  AllergyIntolerance: 10,
  Encounter: 12,
  Gender: 8,
  Region: 10,
  Patient: 14,
  Concept: 16,
  PatientGroup: 14,
  ClinicalCategory: 14,
};

function truncateForNode(label, type) {
  const max = LABEL_LIMITS[type] ?? 12;
  const cleaned = label.replace(/\s+/g, " ").trim();
  if (cleaned.length <= max) return cleaned;
  return `${cleaned.slice(0, max - 1)}…`;
}

export function ensureShortLabel(data) {
  const label = data.label || data.type || "Node";
  const short = data.shortLabel || truncateForNode(label, data.type);
  return { ...data, label, shortLabel: short, fullLabel: data.fullLabel || label };
}
