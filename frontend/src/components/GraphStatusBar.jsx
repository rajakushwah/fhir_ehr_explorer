import { getNodeTypeColor } from "@/components/GraphCanvas/layout";

export default function GraphStatusBar({
  stats,
  selectedCount,
  selectedNode,
  loading,
  onExplore,
  onExpand,
}) {
  const typeColor = selectedNode ? getNodeTypeColor(selectedNode.type) : null;
  const shortLabel = selectedNode?.label?.split("\n")[0] ?? selectedNode?.label;
  const canExpand = selectedNode?.expandable && !selectedNode?.expanded;

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
