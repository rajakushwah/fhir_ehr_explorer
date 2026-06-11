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
  if (parentType === "Patient" && childType === "Location") {
    return "LIVES_IN";
  }

  if (parentType === "Location" && childType === "Patient") {
    return "LIVES_IN";
  }

  if (parentType === "Concept" && childType === "Patient") {
    const rel = parentContext.resourceRel || childData.context?.resourceRel;
    if (rel === "HAS_OBSERVATION") return "HAS_OBSERVATION";
    if (rel === "HAS_ALLERGY") return "HAS_ALLERGY";
    return "HAS_CONDITION";
  }

  if (parentType === "Patient" && childType === "ClinicalCategory") {
    const category = childData.context?.category || childData.meta?.category;
    return CATEGORY_REL[category] || "HAS_RESOURCE";
  }

  if (parentType === "ClinicalCategory") {
    const category = parentContext.category;
    if (category && CATEGORY_REL[category]) return CATEGORY_REL[category];
    if (childType === "Concept") {
      return CATEGORY_REL[category] || "CODED_AS";
    }
    return CHILD_TYPE_REL[childType] || "HAS";
  }

  if (parentType === "Concept" && childType === "PatientGroup") {
    return "HAS_CONDITION";
  }

  if (parentType === "Region" && childType === "Patient") {
    return "INCLUDES";
  }

  if (parentType === "Gender" && childType === "Patient") {
    return "INCLUDES";
  }

  if (
    parentType === "Condition" ||
    parentType === "Observation" ||
    parentType === "AllergyIntolerance" ||
    parentType === "Encounter"
  ) {
    if (childType === "PatientGroup") return "COHORT";
    if (childType === "Gender" || childType === "Region") return "FILTER";
  }

  return CHILD_TYPE_REL[childType] || "RELATED_TO";
}
