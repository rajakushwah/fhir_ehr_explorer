import { useMemo } from "react";

const COMMUNITY_COLORS = [
  "#38bdf8",
  "#34d399",
  "#f472b6",
  "#fb923c",
  "#a78bfa",
  "#facc15",
  "#2dd4bf",
  "#f87171",
];

function communityColor(communityId) {
  const index = Number(communityId);
  if (Number.isNaN(index)) return COMMUNITY_COLORS[0];
  return COMMUNITY_COLORS[((index % COMMUNITY_COLORS.length) + COMMUNITY_COLORS.length) % COMMUNITY_COLORS.length];
}

function formatPercent(value) {
  if (value == null) return "—";
  return `${Math.round(Number(value) * 100)}%`;
}

export default function ClinicalIntelligencePanel({
  mode,
  comorbidity,
  similar,
  conceptDrilldown,
  selectedConcept,
  selectedPatientFhirId,
  loading,
  error,
  onClose,
  onSelectConcept,
  onSelectPatient,
  onBackToCohort,
  onBackToNetwork,
  minimized = false,
  onToggleMinimize,
}) {
  const title = mode === "similar" ? "Similar Patients" : "Comorbidity Intelligence";

  const minimizedSubtitle = useMemo(() => {
    if (conceptDrilldown?.concept?.label) return conceptDrilldown.concept.label;
    if (comorbidity?.interpretation) return comorbidity.interpretation;
    if (similar?.anchorPatient?.label) return similar.anchorPatient.label;
    return null;
  }, [conceptDrilldown, comorbidity, similar]);

  const topConcepts = useMemo(() => {
    if (!comorbidity?.concepts?.length) return [];
    return [...comorbidity.concepts]
      .sort((a, b) => b.patientCount - a.patientCount)
      .slice(0, 12);
  }, [comorbidity]);

  if (!mode && !loading) return null;

  if (minimized) {
    return (
      <button
        type="button"
        className="clinical-intelligence-minimized"
        onClick={onToggleMinimize}
        title="Expand Clinical Intelligence panel"
        aria-label="Expand Clinical Intelligence panel"
      >
        <span className="clinical-intelligence-minimized-label">{title}</span>
        {minimizedSubtitle && (
          <span className="clinical-intelligence-minimized-sub">{minimizedSubtitle}</span>
        )}
        <span className="clinical-intelligence-minimized-expand" aria-hidden>
          ▸
        </span>
      </button>
    );
  }

  return (
    <aside className="clinical-intelligence-panel" aria-label={title}>
      <header className="clinical-intelligence-header">
        <div>
          <p className="clinical-intelligence-kicker">Clinical Intelligence</p>
          <h2 className="clinical-intelligence-title">{title}</h2>
        </div>
        <div className="panel-header-actions">
          {onToggleMinimize && (
            <button
              type="button"
              className="panel-icon-btn"
              onClick={onToggleMinimize}
              title="Minimize panel"
              aria-label="Minimize panel"
            >
              −
            </button>
          )}
          <button
            type="button"
            className="panel-icon-btn panel-icon-btn-close"
            onClick={onClose}
            aria-label="Close panel"
          >
            ×
          </button>
        </div>
      </header>

      {loading && <p className="clinical-intelligence-loading">Analyzing graph…</p>}
      {error && <p className="clinical-intelligence-error">{error}</p>}

      {!loading && mode === "comorbidity" && comorbidity && (
        <div className="clinical-intelligence-body">
          {conceptDrilldown && (
            <section className="clinical-intelligence-drilldown">
              <p className="clinical-intelligence-kicker">Condition drill-down</p>
              <strong>{conceptDrilldown.concept?.label}</strong>
              <p className="clinical-intelligence-summary">{conceptDrilldown.summary}</p>
              <ul className="clinical-intelligence-patient-split">
                {conceptDrilldown.withPatients?.map((patient) => (
                  <li
                    key={patient.fhirId}
                    className={`is-with${selectedPatientFhirId === patient.fhirId ? " is-selected" : ""}`}
                  >
                    <button
                      type="button"
                      className="clinical-intelligence-patient-btn"
                      onClick={() => onSelectPatient?.(patient)}
                    >
                      <span className="clinical-intelligence-tag shared">Has condition</span>
                      {patient.label}
                    </button>
                  </li>
                ))}
                {conceptDrilldown.withoutPatients?.map((patient) => (
                  <li
                    key={patient.fhirId}
                    className={`is-without${selectedPatientFhirId === patient.fhirId ? " is-selected" : ""}`}
                  >
                    <button
                      type="button"
                      className="clinical-intelligence-patient-btn"
                      onClick={() => onSelectPatient?.(patient)}
                    >
                      <span className="clinical-intelligence-tag unique">Missing condition</span>
                      {patient.label}
                    </button>
                  </li>
                ))}
              </ul>
              {onBackToNetwork && (
                <button type="button" className="btn-secondary clinical-intelligence-back" onClick={onBackToNetwork}>
                  ← Back to condition network
                </button>
              )}
            </section>
          )}

          {!conceptDrilldown && (
            <>
              <p className="clinical-intelligence-summary">{comorbidity.interpretation}</p>
              <dl className="clinical-intelligence-stats">
                <div>
                  <dt>Patients</dt>
                  <dd>{comorbidity.patientCount?.toLocaleString()}</dd>
                </div>
                <div>
                  <dt>Conditions mapped</dt>
                  <dd>{comorbidity.concepts?.length ?? 0}</dd>
                </div>
                <div>
                  <dt>Co-occurrence links</dt>
                  <dd>{comorbidity.edges?.length ?? 0}</dd>
                </div>
              </dl>

              {comorbidity.communities?.length > 0 && (
                <section className="clinical-intelligence-section">
                  <h3>Disease clusters</h3>
                  <ul className="clinical-intelligence-list">
                    {comorbidity.communities.map((community) => (
                      <li key={community.id}>
                        <span
                          className="clinical-intelligence-dot"
                          style={{ backgroundColor: communityColor(community.id) }}
                          aria-hidden
                        />
                        <div>
                          <strong>{community.label}</strong>
                          <p>{community.conceptCount} conditions · up to {community.maxPrevalence} patients</p>
                        </div>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {comorbidity.bridges?.length > 0 && (
                <section className="clinical-intelligence-section">
                  <h3>Bridge conditions</h3>
                  <p className="clinical-intelligence-hint">
                    These connect separate clusters — useful screening or intervention targets.
                  </p>
                  <ul className="clinical-intelligence-list">
                    {comorbidity.bridges.map((bridge) => (
                      <li key={bridge.id}>
                        <strong>{bridge.label}</strong>
                        <p>
                          {bridge.patientCount} patients · betweenness {bridge.betweenness}
                        </p>
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </>
          )}

          {topConcepts.length > 0 && (
            <section className="clinical-intelligence-section">
              <h3>Top conditions</h3>
              <ul className="clinical-intelligence-concepts">
                {topConcepts.map((concept) => (
                  <li key={concept.id}>
                    <button
                      type="button"
                      className={`clinical-intelligence-concept-btn${
                        selectedConcept?.id === concept.id ? " is-selected" : ""
                      }`}
                      onClick={() => onSelectConcept?.(concept)}
                    >
                      <span
                        className="clinical-intelligence-dot"
                        style={{ backgroundColor: communityColor(concept.communityId) }}
                        aria-hidden
                      />
                      <span className="clinical-intelligence-concept-label">{concept.label}</span>
                      <span className="clinical-intelligence-concept-meta">
                        {concept.patientCount}/{comorbidity.patientCount} · {formatPercent(concept.prevalence)}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {onBackToCohort && (
            <button type="button" className="btn-secondary clinical-intelligence-back" onClick={onBackToCohort}>
              ← Back to cohort graph
            </button>
          )}
        </div>
      )}

      {!loading && mode === "similar" && similar && (
        <div className="clinical-intelligence-body">
          {similar.anchorPatient && (
            <div className="clinical-intelligence-anchor">
              <p className="clinical-intelligence-kicker">Anchor patient</p>
              <strong>{similar.anchorPatient.label}</strong>
            </div>
          )}

          {similar.patients?.length === 0 && (
            <p className="clinical-intelligence-hint">No similar patients found with shared conditions.</p>
          )}

          {similar.patients?.length > 0 && (
            <section className="clinical-intelligence-section">
              <h3>Most similar patients</h3>
              <ul className="clinical-intelligence-similar-list">
                {similar.patients.map((patient) => (
                  <li key={patient.fhirId}>
                    <button
                      type="button"
                      className="clinical-intelligence-similar-btn"
                      onClick={() => onSelectPatient?.(patient)}
                    >
                      <div className="clinical-intelligence-similar-head">
                        <strong>{patient.label}</strong>
                        <span>{Math.round(patient.score * 100)}% match</span>
                      </div>
                      {patient.sharedConditions?.length > 0 && (
                        <p>
                          <span className="clinical-intelligence-tag shared">Shared</span>
                          {patient.sharedConditions.slice(0, 4).join(", ")}
                        </p>
                      )}
                      {patient.uniqueConditions?.length > 0 && (
                        <p>
                          <span className="clinical-intelligence-tag unique">They also have</span>
                          {patient.uniqueConditions.slice(0, 3).join(", ")}
                        </p>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {onBackToCohort && (
            <button type="button" className="btn-secondary clinical-intelligence-back" onClick={onBackToCohort}>
              ← Back to cohort graph
            </button>
          )}
        </div>
      )}
    </aside>
  );
}

export { communityColor };
