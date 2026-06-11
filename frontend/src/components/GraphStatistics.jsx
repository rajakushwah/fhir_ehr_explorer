import { LEGEND_ITEMS } from "@/components/GraphLegend";
import { getNodeTypeColor } from "@/components/GraphCanvas/layout";

function formatCount(value) {
  return (value ?? 0).toLocaleString();
}

export const PATIENT_EXPAND_LIMITS = [25, 50, 100, 200, 500];

export default function GraphStatistics({
  stats,
  loading,
  hasGraph,
  minimized,
  expandAllActive = false,
  expandLimit = 50,
  onExpandLimitChange,
  onToggleMinimize,
  onExpandAll,
  onCancelExpandAll,
  onCollapseAll,
  onRelayout,
  onFit,
  onClear,
}) {
  const byType = stats.byType ?? {};
  const typeRows = LEGEND_ITEMS.map(({ type, label }) => ({
    type,
    label,
    count: byType[type] ?? 0,
  })).sort((a, b) => b.count - a.count || a.type.localeCompare(b.type));

  if (minimized) {
    return (
      <aside className="graph-stats-panel is-minimized">
        <button
          type="button"
          className="graph-stats-restore"
          onClick={onToggleMinimize}
          title="Show graph statistics"
          aria-label="Expand graph statistics panel"
        >
          <span className="graph-stats-restore-icon" aria-hidden>
            ›
          </span>
          <span className="graph-stats-restore-text">Stats</span>
          <span className="graph-stats-restore-meta">
            {formatCount(stats.nodes)} nodes
          </span>
        </button>
      </aside>
    );
  }

  return (
    <aside className="graph-stats-panel">
      <div className="graph-stats-header">
        <h2 className="graph-stats-title">Graph Statistics</h2>
        <button
          type="button"
          className="panel-icon-btn"
          onClick={onToggleMinimize}
          title="Minimize panel"
          aria-label="Minimize graph statistics panel"
        >
          −
        </button>
      </div>

      <dl className="graph-stats-summary">
        <div className="graph-stat-row">
          <dt>Total Nodes</dt>
          <dd>{formatCount(stats.nodes)}</dd>
        </div>
        <div className="graph-stat-row">
          <dt>Visible Nodes</dt>
          <dd>{formatCount(stats.visibleNodes ?? stats.nodes)}</dd>
        </div>
        <div className="graph-stat-row">
          <dt>Relationships</dt>
          <dd>{formatCount(stats.edges)}</dd>
        </div>
      </dl>

      <div className="graph-stats-scroll">
        <div className="graph-stats-section">
          <h3 className="graph-stats-heading">Node Types</h3>
          <ul className="graph-type-list">
            {typeRows.map(({ type, label, count }) => (
              <li key={type} className={count === 0 ? "is-empty" : ""}>
                <span
                  className="graph-type-dot"
                  style={{ backgroundColor: getNodeTypeColor(type) }}
                  aria-hidden
                />
                <span className="graph-type-name" title={label}>
                  {label}
                </span>
                <span className="graph-type-count">{formatCount(count)}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="graph-stats-bottom">
        {expandAllActive ? (
          <p className="graph-stats-loading graph-stats-loading-active">
            Expanding all nodes…{" "}
            <button
              type="button"
              className="graph-stats-cancel-link"
              onClick={onCancelExpandAll}
            >
              Cancel
            </button>
          </p>
        ) : (
          loading && <p className="graph-stats-loading">Expanding…</p>
        )}

        <label className="graph-stats-field">
          <span className="graph-stats-field-label">Patients per expand</span>
          <select
            className="graph-stats-select"
            value={expandLimit}
            onChange={(e) => onExpandLimitChange?.(Number(e.target.value))}
            disabled={!hasGraph}
            title="Maximum patient nodes loaded when expanding gender or region"
          >
            {PATIENT_EXPAND_LIMITS.map((value) => (
              <option key={value} value={value}>
                {value} patients
              </option>
            ))}
          </select>
        </label>

        <div className="graph-stats-actions">
          {expandAllActive ? (
            <button
              type="button"
              className="graph-stats-btn graph-stats-btn-danger"
              onClick={onCancelExpandAll}
              title="Stop expanding all nodes"
            >
              <span className="graph-stats-btn-icon" aria-hidden>
                ■
              </span>
              Cancel Expand All
            </button>
          ) : (
            <button
              type="button"
              className="graph-stats-btn"
              onClick={onExpandAll}
              disabled={!hasGraph || loading}
              title="Expand all expandable nodes"
            >
              <span className="graph-stats-btn-icon" aria-hidden>
                ⊞
              </span>
              Expand All
            </button>
          )}
          <button
            type="button"
            className="graph-stats-btn"
            onClick={onCollapseAll}
            disabled={!hasGraph || (loading && !expandAllActive)}
            title="Collapse graph to root node"
          >
            <span className="graph-stats-btn-icon" aria-hidden>
              ⊟
            </span>
            Collapse All
          </button>
          <button
            type="button"
            className="graph-stats-btn graph-stats-btn-primary"
            onClick={onRelayout}
            disabled={!hasGraph || (loading && !expandAllActive)}
            title="Re-run force-directed layout"
          >
            <span className="graph-stats-btn-icon" aria-hidden>
              ◎
            </span>
            Force Directed
          </button>
        </div>

        <div className="graph-stats-footer">
          <button type="button" className="graph-stats-link" onClick={onFit} disabled={!hasGraph}>
            Fit view
          </button>
          <button type="button" className="graph-stats-link danger" onClick={onClear} disabled={!hasGraph}>
            Clear graph
          </button>
        </div>

        <p className="graph-stats-hint">
          Double-click to drill down. Increasing the limit reloads patient nodes automatically; or double-click the region/gender node again.
        </p>
      </div>
    </aside>
  );
}
