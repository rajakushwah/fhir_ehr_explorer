/** Soft classic pastel palette for graph nodes. */

export const NODE_TYPE_COLORS = {
  AllergyIntolerance: "#F4D4CC",
  Concept: "#DCE8C8",
  Condition: "#F8E8C4",
  DiagnosticReport: "#D4E4F7",
  Encounter: "#F0DCE8",
  Immunization: "#C8E8F0",
  Location: "#F0E0EC",
  MedicationRequest: "#F5D8E4",
  Observation: "#C8E6EA",
  Organization: "#E8DDD0",
  Patient: "#E6D9C8",
  Practitioner: "#D8E0F5",
  Procedure: "#DCD8F5",
  // UI filter / hub nodes
  PatientGroup: "#E4DCF5",
  Gender: "#E0E8F5",
  Region: "#D8E4F8",
  ClinicalCategory: "#E0DCF8",
};

/** Readable label text on light node fills */
export const NODE_LABEL_COLOR = "#4A5F7A";

export const NODE_DEFAULT_COLOR = "#E4DCF5";

export function getNodeTypeColor(type) {
  return NODE_TYPE_COLORS[type] ?? NODE_DEFAULT_COLOR;
}

export function nodeBorderColor(type) {
  const fill = getNodeTypeColor(type);
  return `${fill}cc`;
}
