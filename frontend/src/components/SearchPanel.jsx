import { useCallback, useEffect, useState } from "react";
import { searchConcepts } from "@/api/api";

const SUGGESTIONS = [
  "diabetes",
  "asthma",
  "hypertension",
  "lupus",
  "covid",
  "glucose",
  "allergy",
];

export default function SearchPanel({ onSelect, backendOnline }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const runSearch = useCallback(async (q) => {
    const trimmed = q.trim();
    if (!trimmed) {
      setResults([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await searchConcepts(trimmed);
      setResults(data);
    } catch (err) {
      setError(err.message);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => runSearch(query), 350);
    return () => clearTimeout(timer);
  }, [query, runSearch]);

  return (
    <aside className="panel search-panel">
      <div className="panel-header">
        <h1>EHR Data Explorer</h1>
        <p className="subtitle">Search clinical concepts and expand patient relationships</p>
      </div>

      <div className={`status-badge ${backendOnline ? "online" : "offline"}`}>
        <span className="status-dot" />
        {backendOnline ? "Backend connected" : "Backend offline"}
      </div>

      <div className="search-field">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search disease, lab, allergy…"
          autoFocus
        />
        {loading && <span className="search-spinner" aria-hidden />}
      </div>

      {error && <p className="error-text">{error}</p>}

      <div className="suggestions">
        {SUGGESTIONS.map((term) => (
          <button
            key={term}
            type="button"
            className="chip"
            onClick={() => setQuery(term)}
          >
            {term}
          </button>
        ))}
      </div>

      <div className="results-list">
        {results.length === 0 && query.trim() && !loading && !error && (
          <p className="empty-text">No concepts found</p>
        )}
        {results.map((item) => (
          <button
            key={`${item.conceptSystem}|${item.conceptCode}`}
            type="button"
            className="result-item"
            onClick={() => onSelect(item)}
          >
            <span className="result-type">Concept</span>
            <span className="result-label">{item.label}</span>
            <span className="result-id">{item.conceptCode}</span>
          </button>
        ))}
      </div>
    </aside>
  );
}
