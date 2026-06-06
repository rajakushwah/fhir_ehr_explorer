/** Neo4j-style relationship labels for graph expand edges. */

const CATEGORY_REL = {
  conditions: "HAS_CONDITION",
  observations: "HAS_OBSERVATION",
  allergies: "HAS_ALLERGY",
  encounters: "HAS_ENCOUNTER",
};

const CHILD_TYPE_REL = {
  Condition: "HAS_CONDITION",
  Observation: "HAS_OBSERVATION",
  AllergyIntolerance: "HAS_ALLERGY",
  Encounter: "HAS_ENCOUNTER",
  Patient: "INCLUDES",
  ClinicalCategory: "HAS_RESOURCE",
  Gender: "FILTER",
  Region: "FILTER",
  PatientGroup: "COHORT",
  Concept: "CODED_AS",
};

/**
 * Resolve edge label when expanding parent → child.
 */
export function resolveEdgeRel(parentType, childType, parentContext = {}, childData = {}) {
  if (parentType === "Patient" && childType === "ClinicalCategory") {
    const category = childData.context?.category || childData.meta?.category;
    return CATEGORY_REL[category] || "HAS_RESOURCE";
  }

  if (parentType === "ClinicalCategory") {
    const category = parentContext.category;
    if (category && CATEGORY_REL[category]) return CATEGORY_REL[category];
    return CHILD_TYPE_REL[childType] || "HAS";
  }

  if (parentType === "Concept" && childType === "PatientGroup") {
    return "HAS_CONDITION";
  }

  if (parentType === "Region" && childType === "Patient") {
    return "INCLUDES";
  }

  if (
    parentType === "Condition" ||
    parentType === "Observation" ||
    parentType === "AllergyIntolerance"
  ) {
    if (childType === "PatientGroup") return "COHORT";
  }

  return CHILD_TYPE_REL[childType] || "RELATED_TO";
}
