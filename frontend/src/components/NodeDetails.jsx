import { useState } from "react";
import { getNodeTypeColor } from "./GraphCanvas/layout";

const TYPE_LABELS = {
  Concept: "Clinical Concept",
  CodeableConcept: "Medical Concept",
  PatientGroup: "Patient Group",
  Gender: "Gender",
  Region: "Region",
  Patient: "Patient",
  Condition: "Condition",
  Observation: "Observation",
  AllergyIntolerance: "Allergy",
  ClinicalCategory: "Clinical Group",
  Encounter: "Encounter",
};

const FHIR_DOCS = {
  Patient: "FHIR Patient",
  Condition: "FHIR Condition",
  Observation: "FHIR Observation",
  AllergyIntolerance: "FHIR AllergyIntolerance",
  Encounter: "FHIR Encounter",
  Concept: "Shared clinical concept",
  ClinicalCategory: "Grouped resources",
};

const FIELD_LABELS = {
  clinicalStatus: "Clinical status",
  verificationStatus: "Verification",
  onset: "Onset",
  date: "Date",
  value: "Value",
  status: "Status",
  start: "Start",
  end: "End",
  total: "Total count",
  category: "Category",
  birthDate: "Birth date",
  city: "City",
  state: "State",
  age: "Age",
};

function formatValue(value) {
  if (value == null || value === "") return null;
  const str = String(value);
  if (/^\d{4}-\d{2}-\d{2}T/.test(str)) {
    try {
      return new Date(str).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      });
    } catch {
      return str;
    }
  }
  return str;
}

function MetaRow({ label, value }) {
  const formatted = formatValue(value);
  if (formatted == null) return null;
  return (
    <div className="meta-row">
      <dt>{label}</dt>
      <dd>{formatted}</dd>
    </div>
  );
}

function ContextRows({ context }) {
  if (!context || Object.keys(context).length === 0) return null;
  return (
    <div className="context-rows">
      {Object.entries(context).map(([key, value]) => (
        <MetaRow
          key={key}
          label={FIELD_LABELS[key] ?? key.replace(/([A-Z])/g, " $1").trim()}
          value={value}
        />
      ))}
    </div>
  );
}

export default function NodeDetails({
  node,
  minimized = false,
  onMinimize,
  onExpand,
  onClose,
  compact = false,
}) {
  const [contextOpen, setContextOpen] = useState(false);

  if (!node) {
    return (
      <aside className="panel details-panel empty">
        <h3>Node Details</h3>
        <p>Select a node in the graph to inspect its properties.</p>
      </aside>
    );
  }

  const typeLabel = TYPE_LABELS[node.type] ?? node.type;
  const fhirDoc = FHIR_DOCS[node.type];
  const meta = node.meta ?? {};
  const color = getNodeTypeColor(node.type);

  if (minimized) {
    return (
      <button
        type="button"
        className="graph-details-minimized"
        onClick={onExpand}
        title="Expand node details"
      >
        <span className="mini-type-dot" style={{ backgroundColor: color }} />
        <span className="mini-type-label">{typeLabel}</span>
        <span className="mini-node-label">{node.label}</span>
        <span className="mini-expand">▸</span>
      </button>
    );
  }

  return (
    <aside className={`panel details-panel${compact ? " details-panel-compact" : ""}`}>
      <div className="overlay-panel-header">
        <div className="details-title-row">
          <span className="type-dot" style={{ backgroundColor: color }} />
          <div>
            <span className="type-badge" style={{ backgroundColor: color }}>
              {typeLabel}
            </span>
            {fhirDoc && <span className="fhir-doc-tag">{fhirDoc}</span>}
          </div>
        </div>
        <div className="panel-header-actions">
          {onMinimize && (
            <button
              type="button"
              className="panel-icon-btn"
              onClick={onMinimize}
              title="Minimize"
              aria-label="Minimize panel"
            >
              −
            </button>
          )}
          {onClose && (
            <button
              type="button"
              className="panel-icon-btn panel-icon-btn-close"
              onClick={onClose}
              title="Close"
              aria-label="Close panel"
            >
              ×
            </button>
          )}
        </div>
      </div>

      <h3 className="details-node-title">{node.label}</h3>

      {node.expandable && (
        <p className="expand-hint">
          {node.expanded
            ? "Expanded — double-click another hub to explore"
            : "Double-click to expand connections"}
        </p>
      )}

      {Object.keys(meta).length > 0 && (
        <section className="details-section">
          <h4 className="details-section-title">Properties</h4>
          <dl className="meta-list">
            {Object.entries(meta).map(([k, v]) => (
              <MetaRow key={k} label={FIELD_LABELS[k] ?? k} value={v} />
            ))}
          </dl>
        </section>
      )}

      {node.context && Object.keys(node.context).length > 0 && (
        <section className="details-section">
          <button
            type="button"
            className="details-section-toggle"
            onClick={() => setContextOpen((o) => !o)}
            aria-expanded={contextOpen}
          >
            <span>Technical context</span>
            <span>{contextOpen ? "▾" : "▸"}</span>
          </button>
          {contextOpen && <ContextRows context={node.context} />}
        </section>
      )}
    </aside>
  );
}
