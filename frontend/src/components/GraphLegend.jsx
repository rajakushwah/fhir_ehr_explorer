import { getNodeTypeColor } from "./GraphCanvas/layout";

export const LEGEND_ITEMS = [
  { type: "Concept", label: "Clinical Concept", doc: "Concept node" },
  { type: "PatientGroup", label: "Patient Group", doc: "Cohort filter" },
  { type: "Gender", label: "Gender", doc: "Cohort filter" },
  { type: "Region", label: "Region / State", doc: "Cohort filter" },
  { type: "Patient", label: "Patient", doc: "FHIR Patient" },
  { type: "ClinicalCategory", label: "Clinical Group", doc: "Category hub" },
  { type: "Condition", label: "Condition", doc: "FHIR Condition" },
  { type: "Observation", label: "Observation", doc: "FHIR Observation" },
  { type: "AllergyIntolerance", label: "Allergy", doc: "FHIR AllergyIntolerance" },
  { type: "Encounter", label: "Encounter", doc: "FHIR Encounter" },
  { type: "Procedure", label: "Procedure", doc: "FHIR Procedure" },
  { type: "MedicationRequest", label: "Medication", doc: "FHIR MedicationRequest" },
  { type: "Immunization", label: "Immunization", doc: "FHIR Immunization" },
  { type: "DiagnosticReport", label: "Diagnostic Report", doc: "FHIR DiagnosticReport" },
];

export default function GraphLegend({ minimized, onToggleMinimize }) {
  if (minimized) {
    return (
      <button
        type="button"
        className="graph-legend graph-legend-minimized"
        onClick={onToggleMinimize}
        title="Show node color legend"
      >
        <span className="legend-mini-dots">
          {LEGEND_ITEMS.slice(0, 5).map(({ type }) => (
            <span
              key={type}
              className="legend-mini-dot"
              style={{ backgroundColor: getNodeTypeColor(type) }}
            />
          ))}
        </span>
        <span>Legend</span>
      </button>
    );
  }

  return (
    <aside className="graph-legend">
      <div className="overlay-panel-header">
        <h3>Node types</h3>
        <button
          type="button"
          className="panel-icon-btn"
          onClick={onToggleMinimize}
          title="Minimize legend"
          aria-label="Minimize legend"
        >
          −
        </button>
      </div>
      <ul className="legend-grid">
        {LEGEND_ITEMS.map(({ type, label, doc }) => (
          <li key={type}>
            <span
              className="legend-swatch"
              style={{ backgroundColor: getNodeTypeColor(type) }}
            />
            <span className="legend-text">
              <strong>{label}</strong>
              <span className="legend-doc">{doc}</span>
            </span>
          </li>
        ))}
      </ul>
      <p className="legend-hint">
        Thin blue border = expandable · Double-click to explore
      </p>
    </aside>
  );
}
