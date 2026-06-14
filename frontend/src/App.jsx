import { useCallback, useEffect, useRef, useState } from "react";
import { analyzeComorbidity, checkHealth, findSimilarPatients, getConceptCohortPatients, searchCohort } from "@/api/api";
import ClinicalIntelligencePanel from "@/components/ClinicalIntelligencePanel";
import CohortPanel from "@/components/CohortPanel";
import GraphCanvas from "@/components/GraphCanvas/GraphCanvas";
import GraphFloatingControls from "@/components/GraphFloatingControls";
import GraphLeftToolbar from "@/components/GraphLeftToolbar";
import GraphStatistics from "@/components/GraphStatistics";
import GraphStatusBar from "@/components/GraphStatusBar";
import NodeDetails from "@/components/NodeDetails";
import NodeInspector from "@/components/NodeInspector/NodeInspector";
import PatientResults from "@/components/PatientResults";
import ThemeToggle from "@/components/ThemeToggle";
import { useTheme } from "@/hooks/useTheme";
import { buildGraphFromCohort, canVisualizeCohort } from "@/utils/graphFromCohort";

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
  const [inspectorNode, setInspectorNode] = useState(null);
  const [stats, setStats] = useState({
    nodes: 0,
    edges: 0,
    visibleNodes: 0,
    byType: {},
  });
  const [loading, setLoading] = useState(false);
  const [fitTrigger, setFitTrigger] = useState(0);
  const [expandAllTrigger, setExpandAllTrigger] = useState(0);
  const [expandAllCancelTrigger, setExpandAllCancelTrigger] = useState(0);
  const [expandAllActive, setExpandAllActive] = useState(false);
  const [collapseAllTrigger, setCollapseAllTrigger] = useState(0);
  const [relayoutTrigger, setRelayoutTrigger] = useState(0);
  const [healthStatus, setHealthStatus] = useState({
    backendOnline: true,
    neo4jOnline: true,
    neo4jError: null,
  });
  const [statsOpen, setStatsOpen] = useState(false);
  const [graphLayout, setGraphLayout] = useState("fcose");
  const [zoomLevel, setZoomLevel] = useState(1);
  const [patientExpandLimit, setPatientExpandLimit] = useState(50);
  const [graphNotice, setGraphNotice] = useState(null);
  const [intelligenceMode, setIntelligenceMode] = useState(null);
  const [intelligenceLoading, setIntelligenceLoading] = useState(false);
  const [intelligenceError, setIntelligenceError] = useState(null);
  const [comorbidityResult, setComorbidityResult] = useState(null);
  const [similarResult, setSimilarResult] = useState(null);
  const [conceptDrilldown, setConceptDrilldown] = useState(null);
  const [selectedConcept, setSelectedConcept] = useState(null);
  const [intelligencePanelMinimized, setIntelligencePanelMinimized] = useState(false);
  const [cohortGraphSnapshot, setCohortGraphSnapshot] = useState(null);
  const cyRef = useRef(null);
  const graphApiRef = useRef(null);
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
    const spec = buildGraphFromCohort(result);
    if (!spec) return;
    setSelectedNode(null);
    setInspectorNode(null);
    setIntelligenceMode(null);
    setComorbidityResult(null);
    setSimilarResult(null);
    setConceptDrilldown(null);
    setSelectedConcept(null);
    setIntelligenceError(null);
    setCohortGraphSnapshot(null);
    setRootNode(spec);
    setView("graph");
    setFitTrigger((n) => n + 1);
  }, []);

  const resolveCohortFilters = useCallback(() => {
    const filters = cohortResult?.graphContext?.filters ?? rootNode?.context?.filters ?? {};
    if (cohortResult?.concept) {
      return {
        ...filters,
        conceptSystem: cohortResult.concept.conceptSystem ?? filters.conceptSystem,
        conceptCode: cohortResult.concept.conceptCode ?? filters.conceptCode,
        conceptLabel: cohortResult.concept.label ?? filters.conceptLabel,
        condition: filters.condition ?? cohortResult.concept.label,
      };
    }
    return filters;
  }, [cohortResult, rootNode]);

  const handleAnalyzeComorbidity = useCallback(async () => {
    setIntelligenceLoading(true);
    setIntelligenceError(null);
    try {
      const filters = resolveCohortFilters();
      const data = await analyzeComorbidity(filters);
      if (!data?.patientCount) {
        setIntelligenceError("No patients with conditions matched this cohort.");
        setIntelligenceMode("comorbidity");
        setComorbidityResult(data);
        return;
      }
      setComorbidityResult(data);
      setSimilarResult(null);
      setIntelligenceMode("comorbidity");
      if (rootNode && rootNode.graphMode !== "comorbidity" && rootNode.graphMode !== "similar") {
        setCohortGraphSnapshot(rootNode);
      }
      setRootNode({
        graphMode: "comorbidity",
        label: data.interpretation,
        analytics: data,
        context: { filters },
      });
      setView("graph");
      setFitTrigger((n) => n + 1);
    } catch (err) {
      setIntelligenceError(err instanceof Error ? err.message : "Comorbidity analysis failed");
      setIntelligenceMode("comorbidity");
    } finally {
      setIntelligenceLoading(false);
    }
  }, [resolveCohortFilters, rootNode]);

  const handleFindSimilarPatients = useCallback(async () => {
    const patientFhirId = selectedNode?.context?.patientFhirId;
    if (!patientFhirId) return;

    setIntelligenceLoading(true);
    setIntelligenceError(null);
    try {
      const filters = resolveCohortFilters();
      const data = await findSimilarPatients(patientFhirId, filters, 10);
      setSimilarResult(data);
      setComorbidityResult(null);
      setIntelligenceMode("similar");
      if (rootNode && rootNode.graphMode !== "comorbidity" && rootNode.graphMode !== "similar") {
        setCohortGraphSnapshot(rootNode);
      }
      setRootNode({
        graphMode: "similar",
        label: `Similar patients · ${data.anchorPatient?.label ?? "Patient"}`,
        analytics: data,
        context: { filters, anchorPatientFhirId: patientFhirId },
      });
      setView("graph");
      setFitTrigger((n) => n + 1);
    } catch (err) {
      setIntelligenceError(err instanceof Error ? err.message : "Similar patient search failed");
      setIntelligenceMode("similar");
    } finally {
      setIntelligenceLoading(false);
    }
  }, [resolveCohortFilters, rootNode, selectedNode]);

  const handleConceptDrilldown = useCallback(async (concept) => {
    if (!concept?.system || !concept?.code) return;
    setIntelligenceLoading(true);
    setIntelligenceError(null);
    setSelectedConcept(concept);
    try {
      const filters = resolveCohortFilters();
      const drilldown = await getConceptCohortPatients(filters, concept);
      setConceptDrilldown(drilldown);
      setRootNode({
        graphMode: "comorbidity-drilldown",
        label: drilldown.summary,
        analytics: drilldown,
        context: { filters },
      });
      setView("graph");
      setFitTrigger((n) => n + 1);
    } catch (err) {
      setIntelligenceError(err instanceof Error ? err.message : "Could not load patients for this condition");
    } finally {
      setIntelligenceLoading(false);
    }
  }, [resolveCohortFilters]);

  const handleBackToComorbidityNetwork = useCallback(() => {
    if (!comorbidityResult) return;
    setConceptDrilldown(null);
    setSelectedConcept(null);
    setRootNode({
      graphMode: "comorbidity",
      label: comorbidityResult.interpretation,
      analytics: comorbidityResult,
      context: { filters: resolveCohortFilters() },
    });
    setFitTrigger((n) => n + 1);
  }, [comorbidityResult, resolveCohortFilters]);

  const handleBackToCohortGraph = useCallback(() => {
    if (cohortGraphSnapshot) {
      setRootNode(cohortGraphSnapshot);
      setIntelligenceMode(null);
      setComorbidityResult(null);
      setSimilarResult(null);
      setConceptDrilldown(null);
      setSelectedConcept(null);
      setIntelligenceError(null);
      setFitTrigger((n) => n + 1);
      return;
    }
    if (cohortResult) {
      handleVisualize(cohortResult);
    }
  }, [cohortGraphSnapshot, cohortResult, handleVisualize]);

  const handleCyReady = useCallback((api) => {
    graphApiRef.current = api;
    cyRef.current = api?.cy ?? api;
  }, []);

  const handleZoomIn = useCallback(() => {
    const cy = graphApiRef.current?.cy ?? cyRef.current;
    if (!cy || cy.destroyed()) return;
    cy.zoom({ level: Math.min(cy.maxZoom(), cy.zoom() * 1.2) });
    setZoomLevel(cy.zoom());
  }, []);

  const handleZoomOut = useCallback(() => {
    const cy = graphApiRef.current?.cy ?? cyRef.current;
    if (!cy || cy.destroyed()) return;
    cy.zoom({ level: Math.max(cy.minZoom(), cy.zoom() / 1.2) });
    setZoomLevel(cy.zoom());
  }, []);

  const handleFocusNode = useCallback((node) => {
    graphApiRef.current?.focusNode?.(node);
  }, []);

  const handleRevealNode = useCallback((nodeOrNeighbor) => {
    const api = graphApiRef.current;
    if (!api) return;
    if (nodeOrNeighbor?.isNode?.()) {
      api.expandNode?.(nodeOrNeighbor);
      return;
    }
    if (nodeOrNeighbor?.cyNode) {
      api.expandNode?.(nodeOrNeighbor.cyNode);
    }
  }, []);

  const handleCancelExpandAll = useCallback(() => {
    setExpandAllCancelTrigger((n) => n + 1);
  }, []);

  const handleExpandSelected = useCallback(() => {
    if (!selectedNode?.id) return;
    const cy = graphApiRef.current?.cy ?? cyRef.current;
    const el = cy?.getElementById(selectedNode.id);
    if (el?.length) graphApiRef.current?.expandNode?.(el);
  }, [selectedNode]);

  const handleCollapseSelected = useCallback(() => {
    if (!selectedNode?.id) return;
    const cy = graphApiRef.current?.cy ?? cyRef.current;
    const el = cy?.getElementById(selectedNode.id);
    if (el?.length) graphApiRef.current?.collapseNode?.(el);
  }, [selectedNode]);

  const handleDismissNode = useCallback((node) => {
    graphApiRef.current?.dismissNode?.(node);
    setSelectedNode(null);
    setInspectorNode(null);
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
    setInspectorNode(null);
    setIntelligenceMode(null);
    setComorbidityResult(null);
    setSimilarResult(null);
    setConceptDrilldown(null);
    setSelectedConcept(null);
    setIntelligenceError(null);
    setCohortGraphSnapshot(null);
    setStats({ nodes: 0, edges: 0, visibleNodes: 0, byType: {} });
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
            {view === "graph" && cohortResult && canVisualizeCohort(cohortResult) && (
              <button
                type="button"
                className="btn-secondary top-bar-intelligence-btn"
                onClick={handleAnalyzeComorbidity}
                disabled={intelligenceLoading}
              >
                {intelligenceLoading && intelligenceMode === "comorbidity"
                  ? "Analyzing…"
                  : "Comorbidity Intelligence"}
              </button>
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
                onVisualize={handleVisualize}
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
                      Country: selectedPatient.country,
                      BirthDate: selectedPatient.birthDate,
                      Conditions: selectedPatient.conditions?.join(", "),
                      ...(selectedPatient.criticalFindings?.length
                        ? {
                            CriticalFindings: selectedPatient.criticalFindings
                              .map((f) => {
                                const unit = f.unit ? ` ${f.unit}` : "";
                                const arrow = f.direction === "low" ? "↓" : "↑";
                                return `${f.label} ${arrow} ${f.value}${unit}`;
                              })
                              .join("; "),
                          }
                        : {}),
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
            <div className="graph-main graph-main-bloom">
              <GraphCanvas
                rootNode={rootNode}
                onNodeSelect={(node) => {
                  setSelectedNode(node);
                  if (!node) {
                    setInspectorNode(null);
                  } else {
                    setInspectorNode((prev) => (prev?.id === node.id ? { ...prev, ...node } : prev));
                  }
                }}
                onStatsChange={setStats}
                onLoadingChange={setLoading}
                fitTrigger={fitTrigger}
                expandAllTrigger={expandAllTrigger}
                expandAllCancelTrigger={expandAllCancelTrigger}
                collapseAllTrigger={collapseAllTrigger}
                relayoutTrigger={relayoutTrigger}
                layoutMode={graphLayout}
                expandLimit={patientExpandLimit}
                visible={view === "graph"}
                theme={theme}
                onCyReady={handleCyReady}
                onZoomChange={setZoomLevel}
                onExpandAllActivityChange={setExpandAllActive}
                onExpandNotice={(message) => {
                  setGraphNotice(message);
                  window.setTimeout(() => setGraphNotice(null), 8000);
                }}
                onConceptDrilldown={handleConceptDrilldown}
              />

              <GraphLeftToolbar
                statsOpen={statsOpen}
                onToggleStats={() => setStatsOpen((o) => !o)}
                onRelayout={() => setRelayoutTrigger((n) => n + 1)}
                onExpandAll={() => setExpandAllTrigger((n) => n + 1)}
                onCancelExpandAll={handleCancelExpandAll}
                expandAllActive={expandAllActive}
                onCollapseAll={() => setCollapseAllTrigger((n) => n + 1)}
                onClear={handleClearGraph}
                disabled={!rootNode}
                expandDisabled={!rootNode || (loading && !expandAllActive)}
              />

              {statsOpen && (
                <div className="bloom-stats-popover">
                  <GraphStatistics
                    stats={stats}
                    loading={loading}
                    hasGraph={!!rootNode}
                    minimized={false}
                    expandAllActive={expandAllActive}
                    expandLimit={patientExpandLimit}
                    onExpandLimitChange={setPatientExpandLimit}
                    onToggleMinimize={() => setStatsOpen(false)}
                    onExpandAll={() => setExpandAllTrigger((n) => n + 1)}
                    onCancelExpandAll={handleCancelExpandAll}
                    onCollapseAll={() => setCollapseAllTrigger((n) => n + 1)}
                    onRelayout={() => setRelayoutTrigger((n) => n + 1)}
                    onFit={() => setFitTrigger((n) => n + 1)}
                    onClear={handleClearGraph}
                  />
                </div>
              )}

              <GraphStatusBar
                stats={stats}
                selectedCount={selectedNode ? 1 : 0}
                selectedNode={selectedNode}
                loading={loading}
                onExpand={handleExpandSelected}
                onCollapse={handleCollapseSelected}
                onSimilarPatients={handleFindSimilarPatients}
                onExplore={() => {
                  if (selectedNode) setInspectorNode(selectedNode);
                }}
              />

              <GraphFloatingControls
                layout={graphLayout}
                onLayoutChange={(name) => {
                  setGraphLayout(name);
                  setRelayoutTrigger((n) => n + 1);
                }}
                onZoomIn={handleZoomIn}
                onZoomOut={handleZoomOut}
                onFit={() => setFitTrigger((n) => n + 1)}
                zoomLevel={zoomLevel}
              />

              {expandAllActive && (
                <div className="graph-expand-all-banner" role="status">
                  <span className="graph-expand-all-text">Expanding all nodes…</span>
                  <button
                    type="button"
                    className="graph-expand-all-cancel"
                    onClick={handleCancelExpandAll}
                  >
                    Cancel
                  </button>
                </div>
              )}

              {graphNotice && (
                <div className="graph-expand-notice" role="status">
                  {graphNotice}
                </div>
              )}

              {!rootNode && (
                <div className="graph-placeholder">
                  {cohortResult && canVisualizeCohort(cohortResult) ? (
                    <>
                      <p>Visualize your current search result as an interactive graph.</p>
                      <button
                        type="button"
                        className="btn-primary graph-placeholder-btn"
                        onClick={() => handleVisualize(cohortResult)}
                      >
                        Visualize in graph →
                      </button>
                    </>
                  ) : (
                    <p>Run a search and click <strong>Visualize in graph</strong>, or switch back to Patients.</p>
                  )}
                </div>
              )}

              {inspectorNode && (
                <NodeInspector
                  node={inspectorNode}
                  cy={graphApiRef.current?.cy ?? cyRef.current}
                  onClose={() => setInspectorNode(null)}
                  onFocusNode={handleFocusNode}
                  onRevealNode={handleRevealNode}
                  onDismissNode={handleDismissNode}
                  onCollapseNode={handleCollapseSelected}
                />
              )}

              {(intelligenceMode || intelligenceLoading) && (
                <ClinicalIntelligencePanel
                  mode={intelligenceMode}
                  comorbidity={comorbidityResult}
                  similar={similarResult}
                  conceptDrilldown={conceptDrilldown}
                  selectedConcept={selectedConcept}
                  selectedPatientFhirId={selectedNode?.context?.patientFhirId ?? null}
                  loading={intelligenceLoading}
                  error={intelligenceError}
                  onClose={() => {
                    setIntelligenceMode(null);
                    setIntelligenceError(null);
                    setIntelligencePanelMinimized(false);
                  }}
                  minimized={intelligencePanelMinimized}
                  onToggleMinimize={() => setIntelligencePanelMinimized((m) => !m)}
                  onSelectConcept={handleConceptDrilldown}
                  onBackToNetwork={
                    comorbidityResult && conceptDrilldown ? handleBackToComorbidityNetwork : null
                  }
                  onSelectPatient={(patient) => {
                    const nodeId = `ui:patient|${patient.fhirId}`;
                    if (conceptDrilldown) {
                      const el = graphApiRef.current?.focusDrilldownPatient?.(
                        { ...patient, hasCondition: conceptDrilldown.withPatients?.some((p) => p.fhirId === patient.fhirId) },
                        conceptDrilldown.concept?.id
                      );
                      if (el?.length) {
                        setSelectedNode({
                          id: nodeId,
                          type: "Patient",
                          label: patient.label,
                          expandable: true,
                          context: { patientFhirId: patient.fhirId },
                          meta: patient,
                        });
                        setView("graph");
                        return;
                      }
                    }
                    const cy = graphApiRef.current?.cy ?? cyRef.current;
                    const el = cy?.getElementById(nodeId);
                    if (el?.length) {
                      graphApiRef.current?.focusNode?.(el);
                      setSelectedNode({
                        id: nodeId,
                        type: "Patient",
                        label: patient.label,
                        expandable: true,
                        context: { patientFhirId: patient.fhirId },
                        meta: patient,
                      });
                    }
                  }}
                  onBackToCohort={
                    cohortGraphSnapshot || cohortResult ? handleBackToCohortGraph : null
                  }
                />
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
