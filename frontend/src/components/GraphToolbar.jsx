export default function GraphToolbar({ stats, loading, onFit, onClear, onZoomIn, onZoomOut }) {
  return (
    <div className="graph-toolbar">
      <div className="toolbar-stats">
        <span>{stats.nodes} nodes</span>
        <span className="divider">·</span>
        <span>{stats.edges} edges</span>
        {loading && (
          <>
            <span className="divider">·</span>
            <span className="loading-text">Expanding…</span>
          </>
        )}
      </div>

      <div className="toolbar-actions">
        <button type="button" onClick={onZoomIn} title="Zoom in">+</button>
        <button type="button" onClick={onZoomOut} title="Zoom out">−</button>
        <button type="button" onClick={onFit} title="Fit graph to view">
          Fit
        </button>
        <button type="button" onClick={onClear} title="Clear graph">
          Clear
        </button>
      </div>
    </div>
  );
}
