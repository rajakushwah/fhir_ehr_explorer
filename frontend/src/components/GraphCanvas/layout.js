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
  return runLayout(cy, "fcose", focusNode);
}

/** Layout after expanding a node — keeps children in rings around the parent. */
export function runExpandLayout(cy, parentNode, childCount = 0) {
  if (!parentNode || parentNode.empty()) return Promise.resolve();

  const children = parentNode.outgoers().nodes();
  if (children.length === 0) return Promise.resolve();

  const parentPos = parentNode.position();
  const positions = computeChildPositions(parentPos, children.length, {
    baseRadius: Math.max(130, Math.min(220, 70 + childCount * 2.5)),
    ringStep: 105,
    maxPerRing: 14,
  });

  cy.batch(() => {
    children.forEach((child, i) => {
      if (positions[i]) child.position(positions[i]);
    });
  });

  const hood = parentNode.closedNeighborhood().nodes();
  if (hood.length < 3) return Promise.resolve();

  return runLayout(cy, "fcose", parentNode);
}

export function runLayout(cy, name = "fcose", focusNode = null) {
  const collection = focusNode
    ? focusNode.closedNeighborhood().nodes()
    : cy.nodes();

  if (collection.length < 2) return Promise.resolve();

  const base = {
    animate: true,
    animationDuration: 450,
    animationEasing: "ease-out-cubic",
    fit: false,
    padding: 40,
  };

  let layoutConfig;
  if (name === "circle") {
    const outerCount = focusNode ? collection.length - 1 : collection.length;
    layoutConfig = {
      name: "circle",
      ...base,
      radius: Math.max(160, Math.sqrt(Math.max(outerCount, 1)) * 52),
      ...(focusNode
        ? {
            concentric: (node) => (node.same(focusNode) ? 0 : 1),
            levelWidth: () => Math.max(160, Math.sqrt(outerCount) * 52),
          }
        : {}),
    };
  } else if (name === "grid") {
    layoutConfig = { name: "grid", ...base, rows: Math.ceil(Math.sqrt(collection.length)) };
  } else {
    layoutConfig = {
      name: "fcose",
      ...base,
      randomize: false,
      nodeDimensionsIncludeLabels: true,
      quality: "default",
      nodeRepulsion: focusNode ? 12000 : 14000,
      idealEdgeLength: (edge) => {
        const t = edge.target().data("type");
        if (t === "Observation") return 100;
        if (t === "Condition") return 120;
        return 150;
      },
      gravity: focusNode ? 0.08 : 0.2,
      gravityRange: focusNode ? 1.2 : 3.2,
      nestingFactor: 0.1,
      numIter: 2500,
      tile: false,
    };
  }

  const layout = collection.layout(layoutConfig);
  return new Promise((resolve) => {
    layout.one("layoutstop", resolve);
    layout.run();
  });
}

export function computeChildPositions(parentPos, count, options = {}) {
  const { baseRadius = 160, ringStep = 100, maxPerRing = 14 } = options;
  if (count === 0) return [];

  const positions = [];
  let placed = 0;
  let ring = 0;

  while (placed < count) {
    const ringCapacity = Math.min(count - placed, maxPerRing + ring * 4);
    const radius = baseRadius + ring * ringStep;
    const angleOffset = ring * 0.12;
    for (let i = 0; i < ringCapacity; i++) {
      const angle = (2 * Math.PI * i) / ringCapacity - Math.PI / 2 + angleOffset;
      positions.push({
        x: parentPos.x + radius * Math.cos(angle),
        y: parentPos.y + radius * Math.sin(angle),
      });
      placed += 1;
    }
    ring += 1;
  }
  return positions;
}

export { getNodeTypeColor } from "./nodeColors";

const LABEL_LIMITS = {
  Observation: 12,
  Condition: 14,
  AllergyIntolerance: 12,
  Encounter: 14,
  Gender: 18,
  Region: 18,
  Patient: 16,
  Concept: 18,
  PatientGroup: 18,
  ClinicalCategory: 16,
};

function truncateForNode(label, type) {
  const max = LABEL_LIMITS[type] ?? 14;
  const cleaned = label.replace(/\s+/g, " ").trim();
  if (cleaned.length <= max) return cleaned;
  return `${cleaned.slice(0, max - 1)}…`;
}

export function ensureShortLabel(data) {
  const label = data.label || data.type || "Node";
  const short = data.shortLabel || truncateForNode(label, data.type);
  return { ...data, label, shortLabel: short, fullLabel: data.fullLabel || label };
}
