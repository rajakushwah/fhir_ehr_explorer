import { useCallback, useEffect, useMemo, useState } from "react";
import { getCohortFilters } from "@/api/api";

const EXAMPLE_QUERIES = [
  "give me all the critical patients",
  "patients in Boston, Massachusetts, US",
  "female patients with diabetes in Massachusetts",
  "critical patients with high glucose",
  "count of total patients",
  "how many patients with diabetes",
  "count patients by gender",
  "how many observations",
];

function uniqueConditions(conditions = []) {
  const seen = new Set();
  return conditions.filter((c) => {
    const key = (c.label || "").trim().toLowerCase();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export default function CohortPanel({ onSearch, onVisualize, searching, lastResult }) {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState({
    states: [],
    cities: [],
    countries: [],
    genders: [],
    conditions: [],
  });
  const [structured, setStructured] = useState({
    patientId: "",
    condition: "",
    city: "",
    state: "",
    country: "",
    gender: "",
  });
  const [mode, setMode] = useState("ask");
  const [error, setError] = useState(null);

  const conditionOptions = useMemo(
    () => uniqueConditions(filters.conditions),
    [filters.conditions]
  );

  useEffect(() => {
    getCohortFilters()
      .then(setFilters)
      .catch((err) => setError(err.message));
  }, []);

  const runSearch = useCallback(async (payload) => {
    setError(null);
    try {
      await onSearch?.(payload, 0);
    } catch (err) {
      setError(err.message);
    }
  }, [onSearch]);

  const handleAsk = () => {
    if (!query.trim()) return;
    runSearch({ query: query.trim() });
  };

  const handleFilters = () => {
    runSearch({
      patientId: structured.patientId.trim() || undefined,
      condition: structured.condition || undefined,
      city: structured.city || undefined,
      state: structured.state || undefined,
      country: structured.country || undefined,
      gender: structured.gender || undefined,
    });
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAsk();
    }
  };

  return (
    <aside className="sidebar">
      <p className="sidebar-label">Patient cohort intelligence</p>

      <div className="mode-tabs">
        <button
          type="button"
          className={mode === "ask" ? "active" : ""}
          onClick={() => setMode("ask")}
        >
          Ask
        </button>
        <button
          type="button"
          className={mode === "filters" ? "active" : ""}
          onClick={() => setMode("filters")}
        >
          Filters
        </button>
      </div>

      {mode === "ask" ? (
        <>
          <label className="field-label">Describe the patients you want</label>
          <textarea
            className="query-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder='e.g. "give me all the critical patients" or "female patients with diabetes in MA"'
            rows={4}
          />
          <button
            type="button"
            className="btn-primary"
            onClick={handleAsk}
            disabled={searching || !query.trim()}
          >
            {searching ? "Searching…" : "Find patients"}
          </button>
          <div className="examples">
            <span className="examples-label">Try:</span>
            {EXAMPLE_QUERIES.map((ex) => (
              <button
                key={ex}
                type="button"
                className="example-chip"
                onClick={() => setQuery(ex)}
              >
                {ex}
              </button>
            ))}
          </div>
        </>
      ) : (
        <>
          <label className="field-label">Patient ID</label>
          <input
            type="text"
            className="query-input query-input-single"
            value={structured.patientId}
            onChange={(e) => setStructured((s) => ({ ...s, patientId: e.target.value }))}
            placeholder="Short ID (e.g. 16101) or FHIR UUID"
          />

          <label className="field-label">Condition</label>
          <select
            value={structured.condition}
            onChange={(e) => setStructured((s) => ({ ...s, condition: e.target.value }))}
          >
            <option value="">Any condition</option>
            {conditionOptions.slice(0, 50).map((c) => (
              <option key={`${c.conceptSystem}|${c.conceptCode}`} value={c.label}>
                {c.label}
              </option>
            ))}
          </select>

          <label className="field-label">City</label>
          <select
            value={structured.city}
            onChange={(e) => setStructured((s) => ({ ...s, city: e.target.value }))}
          >
            <option value="">Any city</option>
            {filters.cities?.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>

          <label className="field-label">State / Region</label>
          <select
            value={structured.state}
            onChange={(e) => setStructured((s) => ({ ...s, state: e.target.value }))}
          >
            <option value="">Any state</option>
            {filters.states?.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          <label className="field-label">Country</label>
          <select
            value={structured.country}
            onChange={(e) => setStructured((s) => ({ ...s, country: e.target.value }))}
          >
            <option value="">Any country</option>
            {(filters.countries?.length ? filters.countries : ["US"]).map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          {filters.countries?.length === 0 && (
            <p className="field-hint">
              Country not in database yet — run: python -m ingestion.cli backfill-country --yes
            </p>
          )}

          <label className="field-label">Gender</label>
          <select
            value={structured.gender}
            onChange={(e) => setStructured((s) => ({ ...s, gender: e.target.value }))}
          >
            <option value="">Any</option>
            {filters.genders?.map((g) => (
              <option key={g} value={g}>{g}</option>
            ))}
          </select>

          <button
            type="button"
            className="btn-primary"
            onClick={handleFilters}
            disabled={searching}
          >
            {searching ? "Searching…" : "Apply filters"}
          </button>
        </>
      )}

      {error && <p className="error-banner">{error}</p>}

      {lastResult && (
        <div className="result-summary">
          <p className="interpretation">{lastResult.interpretation}</p>
          <p className="result-count">
            {lastResult.queryType === "aggregation" ? (
              <>
                <strong>{lastResult.aggregation?.summary ?? lastResult.total}</strong>
              </>
            ) : (
              <>
                {lastResult.totalMatched != null &&
                (lastResult.hasMore || (lastResult.offset ?? 0) > 0) ? (
                  <>
                    <strong>
                      {(lastResult.offset ?? 0) + 1}–
                      {(lastResult.offset ?? 0) + lastResult.total}
                    </strong>{" "}
                    of <strong>{lastResult.totalMatched}</strong> patients
                  </>
                ) : (
                  <>
                    <strong>{lastResult.totalMatched ?? lastResult.total}</strong> patients
                  </>
                )}
              </>
            )}
          </p>
          {(lastResult.queryType === "aggregation"
            ? lastResult.aggregation?.rows?.length > 0
            : (lastResult.totalMatched ?? lastResult.total) > 0) && (
            <button
              type="button"
              className="btn-secondary"
              onClick={() => onVisualize?.(lastResult)}
            >
              Visualize in graph →
            </button>
          )}
        </div>
      )}
    </aside>
  );
}
