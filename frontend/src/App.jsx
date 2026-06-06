import { useCallback, useEffect, useRef, useState } from "react";
import { checkHealth, searchCohort } from "@/api/api";
import CohortPanel from "@/components/CohortPanel";
import GraphCanvas from "@/components/GraphCanvas/GraphCanvas";
import GraphLegend from "@/components/GraphLegend";
import GraphToolbar from "@/components/GraphToolbar";
import NodeDetails from "@/components/NodeDetails";
import PatientResults from "@/components/PatientResults";
import ThemeToggle from "@/components/ThemeToggle";
import { useTheme } from "@/hooks/useTheme";

const PAGE_SIZE = 50;

export default function App() {
  const { theme, toggleTheme } = useTheme();
  const [view, setView] = useState("cohort");
  const [cohortResult, setCohortResult] = useState(null);
  const [searchPayload, setSearchPayload] = useState(null);
  const [cohortSearching, setCohortSearching] = useState(false);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [rootNode, setRootNode] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [stats, setStats] = useState({ nodes: 0, edges: 0 });
  const [loading, setLoading] = useState(false);
  const [fitTrigger, setFitTrigger] = useState(0);
  const [healthStatus, setHealthStatus] = useState({
    backendOnline: true,
    neo4jOnline: true,
    neo4jError: null,
  });
  const [detailsMinimized, setDetailsMinimized] = useState(false);
  const [legendMinimized, setLegendMinimized] = useState(false);
  const cyRef = useRef(null);
  const resultsTopRef = useRef(null);

  useEffect(() => {
    const refreshHealth = () => checkHealth().then(setHealthStatus);
    refreshHealth();
    const interval = setInterval(refreshHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const executeSearch = useCallback(async (payload, offset = 0) => {
    setCohortSearching(true);
    try {
      const result = await searchCohort({ ...payload, limit: PAGE_SIZE, offset });
      setCohortResult(result);
      setSearchPayload(payload);
      setSelectedPatient(null);
      if (result?.queryType === "list" && result.total > 0) {
        setView("cohort");
      }
      if (offset > 0) {
        resultsTopRef.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
      }
      return result;
    } catch (err) {
      setCohortResult(null);
      throw err;
    } finally {
      setCohortSearching(false);
    }
  }, []);

  const handleVisualize = useCallback((result) => {
    if (!result?.concept) return;
    setSelectedNode(null);
    setDetailsMinimized(false);
    setRootNode({
      conceptSystem: result.concept.conceptSystem,
      conceptCode: result.concept.conceptCode,
      label: result.concept.label,
    });
    setView("graph");
    setFitTrigger((n) => n + 1);
  }, []);

  const handleCyReady = useCallback((cy) => {
    cyRef.current = cy;
  }, []);

  const handleSelectPatient = useCallback((patient) => {
    setSelectedPatient(patient);
    setSelectedNode({
      id: `ui:patient|${patient.fhirId}`,
      type: "Patient",
      label: `Patient (${patient.gender || "?"}, ${patient.state || "?"})`,
      expandable: true,
      context: { patientFhirId: patient.fhirId },
      meta: {
        birthDate: patient.birthDate,
        city: patient.city,
        state: patient.state,
        age: patient.age,
      },
    });
  }, []);

  const handleClearGraph = useCallback(() => {
    setRootNode(null);
    setSelectedNode(null);
    setStats({ nodes: 0, edges: 0 });
  }, []);

  const handlePrevPage = useCallback(() => {
    if (!searchPayload || !cohortResult) return;
    const nextOffset = Math.max(0, (cohortResult.offset ?? 0) - PAGE_SIZE);
    executeSearch(searchPayload, nextOffset);
  }, [searchPayload, cohortResult, executeSearch]);

  const handleNextPage = useCallback(() => {
    if (!searchPayload || !cohortResult?.hasMore) return;
    const nextOffset = (cohortResult.offset ?? 0) + PAGE_SIZE;
    executeSearch(searchPayload, nextOffset);
  }, [searchPayload, cohortResult, executeSearch]);

  const pageStart = cohortResult ? (cohortResult.offset ?? 0) + 1 : 0;
  const pageEnd = cohortResult
    ? (cohortResult.offset ?? 0) + (cohortResult.total ?? 0)
    : 0;

  const statusClass = !healthStatus.backendOnline
    ? "offline"
    : healthStatus.neo4jOnline
      ? "online"
      : "degraded";

  const statusLabel = !healthStatus.backendOnline
    ? "API offline"
    : healthStatus.neo4jOnline
      ? "Connected"
      : "Neo4j offline";

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-brand">
          <img src="/hekma-logo.svg" alt="Hekma" className="brand-logo" />
          <span className="app-header-divider" />
          <span className="app-header-product">EHR Explorer</span>
        </div>
        <div className="app-header-actions">
          <div className={`status-pill ${statusClass}`} title={healthStatus.neo4jError ?? ""}>
            <span className="status-dot" />
            {statusLabel}
          </div>
          <ThemeToggle theme={theme} onToggle={toggleTheme} />
        </div>
      </header>

      {!healthStatus.backendOnline && (
        <div className="system-banner offline">
          {healthStatus.neo4jError ?? "Cannot reach backend API. Start the server on port 8002."}
        </div>
      )}

      {healthStatus.backendOnline && !healthStatus.neo4jOnline && (
        <div className="system-banner degraded">
          {healthStatus.neo4jError ?? "Neo4j is not running. Start your local Neo4j instance to search patients."}
        </div>
      )}

      <div className="app-body">
        <CohortPanel
          onSearch={executeSearch}
          onVisualize={handleVisualize}
          searching={cohortSearching}
          lastResult={cohortResult}
        />

        <main className="main-stage">
          <header className="top-bar">
            <div className="view-toggle">
              <button
                type="button"
                className={view === "cohort" ? "active" : ""}
                onClick={() => setView("cohort")}
              >
                Patients
              </button>
              <button
                type="button"
                className={view === "graph" ? "active" : ""}
                onClick={() => {
                  setView("graph");
                  if (!rootNode) setSelectedNode(null);
                  setFitTrigger((n) => n + 1);
                }}
              >
                Graph
              </button>
            </div>
            {cohortResult?.total > 0 && view === "cohort" && cohortResult.queryType !== "aggregation" && (
              <span className="top-bar-meta">
                {cohortResult.totalMatched > PAGE_SIZE
                  ? `Patients ${pageStart}–${pageEnd} of ${cohortResult.totalMatched}`
                  : `${cohortResult.totalMatched ?? cohortResult.total} patients`}
              </span>
            )}
            {cohortResult?.queryType === "aggregation" && view === "cohort" && (
              <span className="top-bar-meta">Aggregation result</span>
            )}
          </header>

          <div className={`cohort-view${view !== "cohort" ? " view-hidden" : ""}`}>
            <div ref={resultsTopRef} className="cohort-results-pane">
              <PatientResults
                cohortResult={cohortResult}
                selectedId={selectedPatient?.fhirId}
                onSelectPatient={handleSelectPatient}
                loading={cohortSearching}
                onPrevPage={handlePrevPage}
                onNextPage={handleNextPage}
              />
            </div>
            {selectedPatient && (
              <aside className="patient-drawer">
                <NodeDetails
                  node={{
                    id: `ui:patient|${selectedPatient.fhirId}`,
                    type: "Patient",
                    label: `${selectedPatient.gender || "Patient"} · ${selectedPatient.city || ""} ${selectedPatient.state || ""}`.trim(),
                    expandable: true,
                    context: { patientFhirId: selectedPatient.fhirId },
                    meta: {
                      Age: selectedPatient.age,
                      Gender: selectedPatient.gender,
                      City: selectedPatient.city,
                      State: selectedPatient.state,
                      BirthDate: selectedPatient.birthDate,
                      Conditions: selectedPatient.conditions?.join(", "),
                    },
                  }}
                />
                <button
                  type="button"
                  className="btn-secondary full-width"
                  onClick={() => {
                    setSelectedNode(null);
                    setRootNode({
                      patientFhirId: selectedPatient.fhirId,
                      label: `Patient (${selectedPatient.gender}, ${selectedPatient.state})`,
                    });
                    setView("graph");
                    setFitTrigger((n) => n + 1);
                  }}
                >
                  Open in graph explorer →
                </button>
              </aside>
            )}
          </div>

          <div className={`graph-view${view !== "graph" ? " view-hidden" : ""}`}>
            <GraphToolbar
              stats={stats}
              loading={loading}
              onFit={() => setFitTrigger((n) => n + 1)}
              onClear={handleClearGraph}
              onZoomIn={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.25)}
              onZoomOut={() => cyRef.current?.zoom(cyRef.current.zoom() * 0.8)}
            />
            <GraphCanvas
              rootNode={rootNode}
              onNodeSelect={(node) => {
                setSelectedNode(node);
                if (node) setDetailsMinimized(false);
              }}
              onStatsChange={setStats}
              onLoadingChange={setLoading}
              fitTrigger={fitTrigger}
              visible={view === "graph"}
              theme={theme}
              onCyReady={handleCyReady}
            />
            {!rootNode && (
              <div className="graph-placeholder">
                <p>Run a search and click <strong>Visualize in graph</strong>, or switch back to Patients.</p>
              </div>
            )}

            <GraphLegend
              minimized={legendMinimized}
              onToggleMinimize={() => setLegendMinimized((m) => !m)}
            />

            {selectedNode && (
              <div className={`graph-details-float${detailsMinimized ? " is-minimized" : ""}`}>
                <NodeDetails
                  node={selectedNode}
                  compact
                  minimized={detailsMinimized}
                  onMinimize={() => setDetailsMinimized(true)}
                  onExpand={() => setDetailsMinimized(false)}
                  onClose={() => setSelectedNode(null)}
                />
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
