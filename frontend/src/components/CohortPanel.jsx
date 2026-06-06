import { useCallback, useEffect, useState } from "react";
import { getCohortFilters } from "@/api/api";

const EXAMPLE_QUERIES = [
  "female patients with diabetes in Massachusetts",
  "count of total patients",
  "how many patients with diabetes",
  "count patients by gender",
  "how many observations",
];

export default function CohortPanel({ onSearch, onVisualize, searching, lastResult }) {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState({ states: [], genders: [], conditions: [] });
  const [structured, setStructured] = useState({
    condition: "",
    state: "",
    gender: "",
  });
  const [mode, setMode] = useState("ask");
  const [error, setError] = useState(null);

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
      condition: structured.condition || undefined,
      state: structured.state || undefined,
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
            placeholder='e.g. "patients in Massachusetts with diabetes"'
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
          <label className="field-label">Condition</label>
          <select
            value={structured.condition}
            onChange={(e) => setStructured((s) => ({ ...s, condition: e.target.value }))}
          >
            <option value="">Any condition</option>
            {filters.conditions?.slice(0, 30).map((c) => (
              <option key={`${c.conceptSystem}|${c.conceptCode}`} value={c.label}>
                {c.label}
              </option>
            ))}
          </select>

          <label className="field-label">State / Region</label>
          <select
            value={structured.state}
            onChange={(e) => setStructured((s) => ({ ...s, state: e.target.value }))}
          >
            <option value="">Any location</option>
            {filters.states?.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

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
          {lastResult.concept && lastResult.queryType !== "aggregation" && (
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
