export default function GraphLeftToolbar({
  statsOpen,
  onToggleStats,
  onRelayout,
  onExpandAll,
  onCollapseAll,
  onClear,
  disabled,
}) {
  return (
    <div className="bloom-left-toolbar">
      <button
        type="button"
        className={`bloom-tool-btn${statsOpen ? " is-active" : ""}`}
        onClick={onToggleStats}
        title="Graph statistics"
        aria-label="Graph statistics"
      >
        ▤
      </button>
      <button
        type="button"
        className="bloom-tool-btn"
        onClick={onRelayout}
        disabled={disabled}
        title="Re-layout graph"
        aria-label="Re-layout graph"
      >
        ◎
      </button>
      <button
        type="button"
        className="bloom-tool-btn"
        onClick={onExpandAll}
        disabled={disabled}
        title="Expand all"
        aria-label="Expand all"
      >
        ⊞
      </button>
      <button
        type="button"
        className="bloom-tool-btn"
        onClick={onCollapseAll}
        disabled={disabled}
        title="Collapse all"
        aria-label="Collapse all"
      >
        ⊟
      </button>
      <button
        type="button"
        className="bloom-tool-btn bloom-tool-btn-danger"
        onClick={onClear}
        disabled={disabled}
        title="Clear graph"
        aria-label="Clear graph"
      >
        ✕
      </button>
    </div>
  );
}
