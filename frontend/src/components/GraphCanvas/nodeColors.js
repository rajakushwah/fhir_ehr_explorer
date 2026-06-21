/** Soft graph palette — light fills, distinct per type. */

export const NODE_TYPE_COLORS = {
  AllergyIntolerance: "#F4A5A5",
  Concept: "#A8DDA8",
  Condition: "#F5D078",
  DiagnosticReport: "#8ED4E8",
  Encounter: "#D4A8D4",
  Immunization: "#8BB8F0",
  Location: "#D4C4A8",
  MedicationRequest: "#EBA8C4",
  Observation: "#98CEDC",
  Organization: "#B8BEC6",
  Patient: "#F5B898",
  Practitioner: "#88B8AC",
  Procedure: "#98B8E8",
  // UI filter / hub nodes
  PatientGroup: "#C4B0E0",
  Gender: "#92B8E8",
  Region: "#98C8E8",
  ClinicalCategory: "#C8B0D8",
};

/** Dark labels read well on light fills */
export const NODE_LABEL_COLOR = "#3D5166";

export const NODE_DEFAULT_COLOR = "#B8BEC6";

export function getNodeTypeColor(type) {
  return NODE_TYPE_COLORS[type] ?? NODE_DEFAULT_COLOR;
}

export function nodeBorderColor(type) {
  return getNodeTypeColor(type);
}
