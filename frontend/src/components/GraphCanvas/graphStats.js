/** Aggregate Cytoscape element counts for the statistics panel. */
export function computeGraphStats(cy) {
  if (!cy || cy.destroyed()) {
    return { nodes: 0, edges: 0, visibleNodes: 0, byType: {} };
  }

  const byType = {};
  cy.nodes().forEach((node) => {
    const type = node.data("type") || "Unknown";
    byType[type] = (byType[type] ?? 0) + 1;
  });

  const visibleNodes = cy.nodes().not(".dimmed").length;

  return {
    nodes: cy.nodes().length,
    edges: cy.edges().length,
    visibleNodes,
    byType,
  };
}
