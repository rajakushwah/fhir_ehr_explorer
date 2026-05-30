function formatAggregationValue(metric, value) {
  if (metric === "avg") {
    return Number.isInteger(value) ? value : value.toFixed(1);
  }
  return Number(value).toLocaleString();
}

export default function PatientResults({
  cohortResult,
  selectedId,
  onSelectPatient,
  loading = false,
  onPrevPage,
  onNextPage,
}) {
  if (!cohortResult) {
    return (
      <div className="results-empty">
        <div className="empty-icon">🔍</div>
        <h2>Find your patient cohort</h2>
        <p>
          Use natural language or filters on the left — for example,
          &quot;female patients with diabetes in Massachusetts&quot;.
        </p>
        <p className="hint">
          Try aggregations too: &quot;count of total patients&quot;,
          &quot;how many observations&quot;, or &quot;count patients by gender&quot;.
        </p>
      </div>
    );
  }

  const { patients, total, totalMatched, interpretation, queryType, aggregation } =
    cohortResult;

  if (queryType === "aggregation" && aggregation) {
    const isGrouped = aggregation.rows.length > 1;
    const maxValue = Math.max(...aggregation.rows.map((r) => r.value), 1);

    return (
      <div className="patient-results aggregation-results">
        <header className="results-header">
          <h2>{interpretation}</h2>
          <span className="badge badge-aggregation">{aggregation.summary}</span>
        </header>

        <div className="aggregation-hero">
          {!isGrouped && (
            <span className="aggregation-big-number">
              {formatAggregationValue(aggregation.metric, aggregation.rows[0]?.value ?? total)}
            </span>
          )}
          {isGrouped && (
            <span className="aggregation-big-number">{totalMatched?.toLocaleString() ?? total}</span>
          )}
          <span className="aggregation-hero-label">
            {isGrouped ? "total across groups" : aggregation.summary}
          </span>
        </div>

        <div className={`aggregation-table${isGrouped ? "" : " single-row"}`}>
          {aggregation.rows.map((row) => (
            <div key={row.label} className="aggregation-row">
              <div className="aggregation-row-head">
                <span className="aggregation-label">{row.label}</span>
                <span className="aggregation-value">
                  {formatAggregationValue(aggregation.metric, row.value)}
                </span>
              </div>
              {isGrouped && (
                <div className="aggregation-bar-track">
                  <div
                    className="aggregation-bar-fill"
                    style={{ width: `${(row.value / maxValue) * 100}%` }}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (total === 0) {
    return (
      <div className="results-empty">
        <div className="empty-icon">∅</div>
        <h2>No patients matched</h2>
        <p>{interpretation}</p>
        <p className="hint">
          Try broadening location or condition terms. Sample data uses US states
          (e.g. MA, Massachusetts) — not international locations.
        </p>
      </div>
    );
  }

  const showingTruncated = totalMatched != null && totalMatched > total;
  const offset = cohortResult.offset ?? 0;
  const hasMore = cohortResult.hasMore ?? false;
  const pageStart = offset + 1;
  const pageEnd = offset + total;
  const canPrev = offset > 0;

  return (
    <div className={`patient-results${loading ? " is-loading" : ""}`}>
      <header className="results-header">
        <h2>{interpretation}</h2>
        <span className="badge">
          {showingTruncated || hasMore || canPrev
            ? `${pageStart}–${pageEnd} of ${totalMatched.toLocaleString()}`
            : `${totalMatched ?? total} patients`}
        </span>
      </header>
      {(showingTruncated || hasMore || canPrev) && (
        <p className="results-truncation-hint">
          Showing patients {pageStart}–{pageEnd} of {totalMatched.toLocaleString()}.
          Use Next to load more.
        </p>
      )}
      <div className="patient-grid">
        {patients.map((p) => (
          <button
            key={p.fhirId}
            type="button"
            className={`patient-card ${selectedId === p.fhirId ? "selected" : ""}`}
            onClick={() => onSelectPatient?.(p)}
            disabled={loading}
          >
            <div className="patient-card-top">
              <span className="patient-avatar">
                {(p.gender || "?")[0].toUpperCase()}
              </span>
              <div>
                <span className="patient-id">Patient</span>
                <span className="patient-meta">
                  {[p.gender, p.age != null ? `age ${p.age}` : null, p.city, p.state]
                    .filter(Boolean)
                    .join(" · ")}
                </span>
              </div>
            </div>
            {p.conditions?.length > 0 && (
              <div className="condition-tags">
                {p.conditions.slice(0, 2).map((c) => (
                  <span key={c} className="tag">{c}</span>
                ))}
                {p.conditions.length > 2 && (
                  <span className="tag muted">+{p.conditions.length - 2}</span>
                )}
              </div>
            )}
          </button>
        ))}
      </div>
      {(canPrev || hasMore) && (
        <nav className="results-pagination" aria-label="Patient list pages">
          <button
            type="button"
            className="btn-secondary pagination-btn"
            onClick={onPrevPage}
            disabled={!canPrev || loading}
          >
            ← Previous
          </button>
          <span className="pagination-meta">
            {loading ? "Loading…" : `Page ${Math.floor(offset / (cohortResult.limit || 50)) + 1} · ${pageStart}–${pageEnd} of ${totalMatched.toLocaleString()}`}
          </span>
          <button
            type="button"
            className="btn-secondary pagination-btn"
            onClick={onNextPage}
            disabled={!hasMore || loading}
          >
            Next →
          </button>
        </nav>
      )}
    </div>
  );
}
