CREATE CONSTRAINT patient_fhir_id IF NOT EXISTS
FOR (p:Patient) REQUIRE p.fhirId IS UNIQUE;

CREATE CONSTRAINT concept_system_code IF NOT EXISTS
FOR (c:Concept) REQUIRE (c.system, c.code) IS UNIQUE;

CREATE CONSTRAINT condition_fhir_id IF NOT EXISTS
FOR (c:Condition) REQUIRE c.fhirId IS UNIQUE;

CREATE CONSTRAINT observation_fhir_id IF NOT EXISTS
FOR (o:Observation) REQUIRE o.fhirId IS UNIQUE;

CREATE CONSTRAINT encounter_fhir_id IF NOT EXISTS
FOR (e:Encounter) REQUIRE e.fhirId IS UNIQUE;

CREATE CONSTRAINT procedure_fhir_id IF NOT EXISTS
FOR (p:Procedure) REQUIRE p.fhirId IS UNIQUE;

CREATE CONSTRAINT medication_request_fhir_id IF NOT EXISTS
FOR (m:MedicationRequest) REQUIRE m.fhirId IS UNIQUE;

CREATE CONSTRAINT allergy_fhir_id IF NOT EXISTS
FOR (a:AllergyIntolerance) REQUIRE a.fhirId IS UNIQUE;

CREATE CONSTRAINT immunization_fhir_id IF NOT EXISTS
FOR (i:Immunization) REQUIRE i.fhirId IS UNIQUE;

CREATE CONSTRAINT diagnostic_report_fhir_id IF NOT EXISTS
FOR (d:DiagnosticReport) REQUIRE d.fhirId IS UNIQUE;

CREATE CONSTRAINT organization_fhir_id IF NOT EXISTS
FOR (o:Organization) REQUIRE o.fhirId IS UNIQUE;

CREATE CONSTRAINT location_fhir_id IF NOT EXISTS
FOR (l:Location) REQUIRE l.fhirId IS UNIQUE;

CREATE CONSTRAINT practitioner_fhir_id IF NOT EXISTS
FOR (p:Practitioner) REQUIRE p.fhirId IS UNIQUE;

CREATE INDEX patient_state IF NOT EXISTS FOR (p:Patient) ON (p.state);
CREATE INDEX patient_gender IF NOT EXISTS FOR (p:Patient) ON (p.gender);
CREATE INDEX obs_effective IF NOT EXISTS FOR (o:Observation) ON (o.effectiveDateTime);
CREATE INDEX condition_onset IF NOT EXISTS FOR (c:Condition) ON (c.onsetDateTime);

CREATE FULLTEXT INDEX conceptSearch IF NOT EXISTS
FOR (c:Concept) ON EACH [c.display, c.text];
