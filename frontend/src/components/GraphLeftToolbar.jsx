export default function GraphLeftToolbar({
  statsOpen,
  onToggleStats,
  onRelayout,
  onExpandAll,
  onCancelExpandAll,
  expandAllActive = false,
  onCollapseAll,
  onClear,
  disabled,
  expandDisabled,
}) {
  const graphDisabled = disabled && !expandAllActive;
  const expandBtnDisabled = expandDisabled ?? graphDisabled;

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
        disabled={graphDisabled}
        title="Re-layout graph"
        aria-label="Re-layout graph"
      >
        ◎
      </button>
      {expandAllActive ? (
        <button
          type="button"
          className="bloom-tool-btn bloom-tool-btn-danger"
          onClick={onCancelExpandAll}
          title="Cancel expand all"
          aria-label="Cancel expand all"
        >
          ■
        </button>
      ) : (
        <button
          type="button"
          className="bloom-tool-btn"
          onClick={onExpandAll}
          disabled={expandBtnDisabled}
          title="Expand all"
          aria-label="Expand all"
        >
          ⊞
        </button>
      )}
      <button
        type="button"
        className="bloom-tool-btn"
        onClick={onCollapseAll}
        disabled={graphDisabled}
        title="Collapse all"
        aria-label="Collapse all"
      >
        ⊟
      </button>
      <button
        type="button"
        className="bloom-tool-btn bloom-tool-btn-danger"
        onClick={onClear}
        disabled={graphDisabled}
        title="Clear graph"
        aria-label="Clear graph"
      >
        ✕
      </button>
    </div>
  );
}
