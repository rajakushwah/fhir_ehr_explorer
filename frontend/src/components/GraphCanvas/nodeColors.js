/** Light FHIR node palette (matches clinical graph legend). */

export const NODE_TYPE_COLORS = {
  AllergyIntolerance: "#E85D3F",
  Concept: "#B3C15B",
  Condition: "#FFC645",
  DiagnosticReport: "#6EA8F2",
  Encounter: "#FFD1F5",
  Immunization: "#89D4F5",
  Location: "#F2C6E8",
  MedicationRequest: "#F591BC",
  Observation: "#00ACC1",
  Organization: "#D7BFA5",
  Patient: "#C2A679",
  Practitioner: "#9EB8FF",
  Procedure: "#8B8DFA",
  // UI filter / hub nodes
  PatientGroup: "#C7B8F5",
  Gender: "#C7B8F5",
  Region: "#9EB8FF",
  ClinicalCategory: "#8B8DFA",
};

/** Dark label text for light node fills */
export const NODE_LABEL_COLOR = "#203f68";

export function getNodeTypeColor(type) {
  return NODE_TYPE_COLORS[type] ?? "#C7B8F5";
}

export function nodeBorderColor(type) {
  const fill = getNodeTypeColor(type);
  return `${fill}cc`;
}
