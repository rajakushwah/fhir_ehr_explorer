const LAYOUTS = [
  { id: "fcose", label: "Force-based layout" },
  { id: "circle", label: "Circular layout" },
];

export default function GraphFloatingControls({
  layout,
  onLayoutChange,
  onZoomIn,
  onZoomOut,
  onFit,
  zoomLevel,
}) {
  return (
    <div className="bloom-floating-controls">
      <div className="bloom-layout-picker">
        <select
          className="bloom-layout-select"
          value={layout}
          onChange={(e) => onLayoutChange?.(e.target.value)}
          aria-label="Graph layout"
        >
          {LAYOUTS.map(({ id, label }) => (
            <option key={id} value={id}>
              {label}
            </option>
          ))}
        </select>
        <span className="bloom-layout-edit" title="Layout settings">✎</span>
      </div>

      <div className="bloom-zoom-stack">
        <button type="button" onClick={onFit} title="Fit to screen" aria-label="Fit to screen">
          ⊡
        </button>
        <button type="button" onClick={onZoomIn} title="Zoom in" aria-label="Zoom in">
          +
        </button>
        <button type="button" onClick={onZoomOut} title="Zoom out" aria-label="Zoom out">
          −
        </button>
        <span className="bloom-zoom-level">{Math.round((zoomLevel ?? 1) * 100)}%</span>
      </div>
    </div>
  );
}

export { LAYOUTS };
