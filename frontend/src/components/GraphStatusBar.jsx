import { getNodeTypeColor } from "@/components/GraphCanvas/layout";

export default function GraphStatusBar({
  stats,
  selectedCount,
  selectedNode,
  loading,
  onExplore,
  onExpand,
  onCollapse,
  onSimilarPatients,
}) {
  const typeColor = selectedNode ? getNodeTypeColor(selectedNode.type) : null;
  const shortLabel = selectedNode?.label?.split("\n")[0] ?? selectedNode?.label;
  const canExpand = selectedNode?.expandable && !selectedNode?.expanded;
  const canCollapse = !!selectedNode?.expanded;
  const canFindSimilar =
    selectedNode?.type === "Patient" && !!selectedNode?.context?.patientFhirId;

  return (
    <div className="bloom-status-bar">
      <span className="bloom-status-item">All ({stats.nodes ?? 0})</span>
      <span className="bloom-status-divider">·</span>
      <span className="bloom-status-item bloom-status-selected">
        Selected ({selectedCount ?? 0})
      </span>

      {selectedNode && (
        <>
          <span className="bloom-status-divider">·</span>
          <span className="bloom-status-selection">
            <span
              className="bloom-status-type-dot"
              style={{ backgroundColor: typeColor }}
              aria-hidden
            />
            <span className="bloom-status-type">{selectedNode.type}</span>
            <span className="bloom-status-label" title={shortLabel}>
              {shortLabel}
            </span>
          </span>
          {canExpand && (
            <button
              type="button"
              className="bloom-expand-btn"
              onClick={onExpand}
              title="Expand to show connected nodes (or double-click the node)"
            >
              Expand
            </button>
          )}
          {canCollapse && (
            <button
              type="button"
              className="bloom-collapse-btn"
              onClick={onCollapse}
              title="Hide connected nodes (or right-click the node)"
            >
              Collapse
            </button>
          )}
          {canFindSimilar && (
            <button
              type="button"
              className="bloom-similar-btn"
              onClick={onSimilarPatients}
              title="Find patients with similar conditions"
            >
              Similar patients
            </button>
          )}
          <button
            type="button"
            className="bloom-explore-btn"
            onClick={onExplore}
            title="Open node inspector (properties, neighbors, relationships)"
          >
            Explore node
          </button>
        </>
      )}

      {loading && (
        <>
          <span className="bloom-status-divider">·</span>
          <span className="bloom-status-loading">Expanding…</span>
        </>
      )}
    </div>
  );
}
