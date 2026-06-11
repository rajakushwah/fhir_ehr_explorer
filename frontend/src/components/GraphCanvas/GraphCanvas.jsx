import { useCallback, useEffect, useRef, useState } from "react";
import Cytoscape from "cytoscape";
import { expandNode } from "@/api/api";
import { getCytoscapeStyles } from "./graphStyles";
import {
  computeChildPositions,
  ensureShortLabel,
  registerFcose,
  runExpandLayout,
  runLayout,
} from "./layout";
import { resolveEdgeRel } from "./edgeLabels";
import { computeGraphStats } from "./graphStats";

registerFcose(Cytoscape);

const CY_BASE_OPTIONS = {
  layout: { name: "preset" },
  wheelSensitivity: 0.2,
  minZoom: 0.15,
  maxZoom: 3,
  motionBlur: false,
  textureOnViewport: false,
  hideEdgesOnViewport: true,
  pixelRatio: 1,
  boxSelectionEnabled: false,
};

function highlightNeighborhood(cy, node, { dimOthers = true } = {}) {
  cy.elements().removeClass("dimmed highlighted");
  cy.edges().removeClass("highlighted");
  if (!node || node.empty()) return;

  const hood = node.closedNeighborhood();
  if (dimOthers) {
    cy.elements().not(hood).addClass("dimmed");
  }
  hood.nodes().addClass("highlighted");
  hood.edges().addClass("highlighted");
}

function fitGraph(cy, padding = 80) {
  if (!cy || cy.destroyed() || cy.nodes().length === 0) return;
  cy.resize();
  cy.fit(undefined, padding);
  cy.center();
}

function deferFit(cy, padding = 80) {
  requestAnimationFrame(() => {
    requestAnimationFrame(() => fitGraph(cy, padding));
  });
}

/** Fit expanded neighborhood, then zoom in so connected nodes are easier to read. */
function focusExpandedNeighborhood(cy, node, { zoomFactor = 2, padding = 72 } = {}) {
  if (!cy || cy.destroyed() || !node || node.empty()) return Promise.resolve();

  const hood = node.closedNeighborhood();
  if (hood.empty()) return Promise.resolve();

  return new Promise((resolve) => {
    cy.animate({
      fit: { eles: hood, padding },
      duration: 320,
      easing: "ease-out-cubic",
      complete: () => {
        const targetZoom = Math.min(cy.maxZoom(), cy.zoom() * zoomFactor);
        cy.animate({
          zoom: targetZoom,
          center: { eles: hood },
          duration: 380,
          easing: "ease-out-cubic",
          complete: resolve,
        });
      },
    });
  });
}

function getPatientChildren(node) {
  return node.outgoers().nodes().filter((child) => child.data("type") === "Patient");
}

function clearDirectChildren(node) {
  node.outgoers().nodes().forEach((child) => child.remove());
  node.data("expanded", false);
  node.removeClass("expanded");
}

/** Collapse an expanded node, removing exclusive descendants and unlinking shared ones. */
function collapseNode(node) {
  if (!node || node.empty() || !node.data("expanded")) {
    return { removedNodes: 0, removedEdges: 0 };
  }

  const cy = node.cy();
  const nodesToRemove = new Set();
  const edgesToRemove = [];

  function visitChild(parent, child) {
    if (!child || child.empty() || child.removed()) return;

    const parentEdges = parent.edgesWith(child).filter((edge) => edge.source().same(parent));
    const incomers = child.incomers("node");

    if (incomers.length > 1) {
      parentEdges.forEach((edge) => edgesToRemove.push(edge));
      return;
    }

    if (nodesToRemove.has(child.id())) return;

    child.outgoers().nodes().forEach((grandchild) => {
      if (!grandchild.same(child)) visitChild(child, grandchild);
    });

    nodesToRemove.add(child.id());
  }

  node.outgoers().nodes().forEach((child) => visitChild(node, child));

  let removedNodes = 0;
  let removedEdges = 0;

  cy.batch(() => {
    edgesToRemove.forEach((edge) => {
      if (edge && !edge.removed()) {
        edge.remove();
        removedEdges += 1;
      }
    });
    nodesToRemove.forEach((id) => {
      const el = cy.getElementById(id);
      if (el.length && !el.removed()) {
        el.remove();
        removedNodes += 1;
      }
    });
    node.data("expanded", false);
    node.removeClass("expanded");
  });

  return { removedNodes, removedEdges };
}

function nodeSelectionPayload(node) {
  if (!node || node.empty()) return null;
  const data = node.data();
  const expandable = data.expandable === true || data.expandable === "true";
  return {
    ...data,
    expandable: expandable && !data.expanded,
    expanded: !!data.expanded,
  };
}

export default function GraphCanvas({
  rootNode,
  onNodeSelect,
  onStatsChange,
  onLoadingChange,
  fitTrigger,
  expandAllTrigger = 0,
  expandAllCancelTrigger = 0,
  collapseAllTrigger = 0,
  relayoutTrigger = 0,
  layoutMode = "fcose",
  expandLimit = 50,
  visible = true,
  onCyReady,
  onExpandNotice,
  onExpandAllActivityChange,
  onZoomChange,
  theme = "dark",
}) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);
  const expandingRef = useRef(new Set());
  const expandAllCancelledRef = useRef(false);
  const expandAllActiveRef = useRef(false);
  const hoveredNodeRef = useRef(null);
  const [tooltip, setTooltip] = useState(null);

  const onNodeSelectRef = useRef(onNodeSelect);
  const onCyReadyRef = useRef(onCyReady);
  const onStatsChangeRef = useRef(onStatsChange);
  const onLoadingChangeRef = useRef(onLoadingChange);
  const expandLimitRef = useRef(expandLimit);
  const layoutModeRef = useRef(layoutMode);
  const onExpandNoticeRef = useRef(onExpandNotice);
  const onExpandAllActivityChangeRef = useRef(onExpandAllActivityChange);
  const onZoomChangeRef = useRef(onZoomChange);
  onExpandNoticeRef.current = onExpandNotice;
  onExpandAllActivityChangeRef.current = onExpandAllActivityChange;
  onZoomChangeRef.current = onZoomChange;
  layoutModeRef.current = layoutMode;
  onNodeSelectRef.current = onNodeSelect;
  onCyReadyRef.current = onCyReady;
  onStatsChangeRef.current = onStatsChange;
  onLoadingChangeRef.current = onLoadingChange;
  expandLimitRef.current = expandLimit;

  const reportStats = useCallback((cy) => {
    if (!cy || cy.destroyed()) return;
    onStatsChangeRef.current?.(computeGraphStats(cy));
  }, []);

  const updateTooltipForNode = useCallback((node) => {
    if (!node || node.empty()) {
      setTooltip(null);
      return;
    }
    const rendered = node.renderedPosition();
    const data = node.data();
    setTooltip({
      x: rendered.x,
      y: rendered.y,
      type: data.type,
      label: data.fullLabel || data.label,
      meta: data.meta,
      expandable: data.expandable && !data.expanded,
      expanded: !!data.expanded,
    });
  }, []);

  const handleExpandRef = useRef(null);

  const isExpandAllCancelled = () =>
    expandAllActiveRef.current && expandAllCancelledRef.current;

  const clearExpandLoadingState = (cy) => {
    if (!cy || cy.destroyed()) return;
    cy.nodes(".loading").removeClass("loading");
    expandingRef.current.clear();
  };

  const handleCollapseRef = useRef(null);

  handleCollapseRef.current = (node) => {
    const cy = cyRef.current;
    if (!cy || cy.destroyed() || !node || node.empty()) return null;
    if (!node.data("expanded")) return null;

    const result = collapseNode(node);
    highlightNeighborhood(cy, node, { dimOthers: true });
    reportStats(cy);
    deferFit(cy, 80);

    const payload = nodeSelectionPayload(node);
    onNodeSelectRef.current?.(payload);
    return { ...result, node: payload };
  };

  handleExpandRef.current = async (node) => {
    const cy = cyRef.current;
    if (isExpandAllCancelled()) return;
    const isExpandable = node.data("expandable") === true || node.data("expandable") === "true";
    const patientChildren = getPatientChildren(node);
    const needsPatientRefresh =
      patientChildren.length > 0
      && patientChildren.length < expandLimitRef.current;

    if (node.data("expanded") && !needsPatientRefresh) return;
    if (!isExpandable && !needsPatientRefresh) return;
    if (expandingRef.current.has(node.id())) return;

    if (needsPatientRefresh) {
      clearDirectChildren(node);
    }

    expandingRef.current.add(node.id());
    node.addClass("loading");
    onLoadingChangeRef.current?.(true);

    try {
      const nodeContext = { ...(node.data("context") ?? {}) };
      const meta = node.data("meta");
      if (meta && typeof meta === "object" && Object.keys(meta).length > 0) {
        nodeContext.meta = meta;
      }
      const limit = expandLimitRef.current;
      const result = await expandNode(node.data("type"), nodeContext, limit);
      if (isExpandAllCancelled()) {
        node.removeClass("loading");
        return;
      }
      const children = result.nodes ?? [];

      if (import.meta.env.DEV) {
        console.info(
          "[Graph] expand",
          node.data("type"),
          `limit=${limit}`,
          `received=${children.length}`
        );
      }

      if (children.length === 0) {
        node.removeClass("loading");
        if (result.message) {
          onExpandNoticeRef.current?.(result.message);
        } else if (import.meta.env.DEV) {
          console.warn("[Graph] expand returned no children", node.data("type"), nodeContext);
        }
        return;
      }

      const parentPos = node.position();
      const positions = computeChildPositions(parentPos, children.length);

      cy.batch(() => {
        children.forEach((child, i) => {
          const childId = child.data?.id ?? child.id;
          const data = ensureShortLabel(child.data ?? child);
          const relType = resolveEdgeRel(
            node.data("type"),
            data.type,
            node.data("context"),
            data
          );
          const edgeId = `${node.id()}->${childId}`;

          if (!cy.getElementById(childId).length) {
            const pos = positions[i] ?? { x: parentPos.x + 140, y: parentPos.y };
            const classes = ["show-label"];
            if (data.expandable) classes.push("expandable");
            if (data.expanded) classes.push("expanded");

            cy.add({
              group: "nodes",
              data,
              position: pos,
              classes: classes.join(" "),
            });
          } else {
            cy.getElementById(childId).addClass("show-label");
          }

          if (!cy.getElementById(edgeId).length) {
            cy.add({
              group: "edges",
              data: {
                id: edgeId,
                source: node.id(),
                target: childId,
                relType,
              },
            });
          }
        });

        node.data("expanded", true);
        node.removeClass("loading");
        node.addClass("expanded show-label");
        node.neighborhood().nodes().addClass("show-label");
      });

      await runExpandLayout(cy, node, children.length);
      if (isExpandAllCancelled()) return;

      highlightNeighborhood(cy, node, { dimOthers: true });
      await focusExpandedNeighborhood(cy, node, { zoomFactor: 2 });
      if (isExpandAllCancelled()) return;
      onZoomChangeRef.current?.(cy.zoom());

      onNodeSelectRef.current?.(nodeSelectionPayload(node));
      reportStats(cy);

      // Auto-continue when a filter hub has only one branch (e.g. all-female cohort).
      if (children.length === 1 && !isExpandAllCancelled()) {
        const childPayload = children[0].data ?? children[0];
        const parentType = node.data("type");
        const autoTypes = new Set(["PatientGroup", "Gender", "Region"]);
        if (autoTypes.has(parentType) && childPayload.expandable) {
          const childId = childPayload.id ?? childPayload.data?.id;
          const childEl = cy.getElementById(childId);
          if (childEl.length && !childEl.data("expanded")) {
            await handleExpandRef.current?.(childEl);
          }
        }
      }
    } catch (err) {
      node.removeClass("loading");
      const message = err instanceof Error ? err.message : "Expand failed";
      onExpandNoticeRef.current?.(message);
      if (import.meta.env.DEV) console.error("[Graph] expand failed", err);
    } finally {
      expandingRef.current.delete(node.id());
      if (!expandAllActiveRef.current) {
        onLoadingChangeRef.current?.(false);
      }
    }
  };

  const addChildNodes = useCallback((cy, parentNode, children) => {
    if (!children?.length) return;

    const parentPos = parentNode.position();
    const positions = computeChildPositions(parentPos, children.length);
    const parentType = parentNode.data("type");
    const parentContext = parentNode.data("context") ?? {};

    cy.batch(() => {
      children.forEach((child, i) => {
        if (cy.getElementById(child.id).length) return;

        const data = ensureShortLabel(child);
        const pos = positions[i] ?? { x: parentPos.x + 140, y: parentPos.y };
        const classes = ["show-label"];
        if (data.expandable) classes.push("expandable");
        if (data.expanded) classes.push("expanded");

        cy.add({
          group: "nodes",
          data,
          position: pos,
          classes: classes.join(" "),
        });

        const relType = resolveEdgeRel(
          parentType,
          data.type,
          parentContext,
          data
        );

        cy.add({
          group: "edges",
          data: {
            id: `${parentNode.id()}->${child.id}`,
            source: parentNode.id(),
            target: child.id,
            relType,
          },
        });
      });

      parentNode.data("expanded", true);
      parentNode.addClass("expanded show-label");
      parentNode.neighborhood().nodes().addClass("show-label");
    });
  }, []);

  const loadRootNode = useCallback(async (cy, nodeSpec) => {
    if (!cy || cy.destroyed() || !nodeSpec) return;

    cy.elements().remove();
    expandingRef.current.clear();
    setTooltip(null);

    let data;
    if (nodeSpec.patientFhirId) {
      data = ensureShortLabel({
        id: `ui:patient|${nodeSpec.patientFhirId}`,
        type: "Patient",
        label: nodeSpec.label || "Patient",
        expandable: true,
        context: { patientFhirId: nodeSpec.patientFhirId },
      });
    } else if (nodeSpec.graphMode === "metric") {
      const key = nodeSpec.context?.cohortKey ?? "metric";
      const filters = nodeSpec.context?.filters ?? {};
      data = ensureShortLabel({
        id: `ui:metric|${nodeSpec.nodeType}|${key}`,
        type: nodeSpec.nodeType,
        label: nodeSpec.label,
        expandable: true,
        context: {
          cohortFilters: filters,
          cohortKey: key,
          metricResource: nodeSpec.nodeType,
        },
      });
    } else if (nodeSpec.graphMode === "cohort") {
      const key = nodeSpec.context?.cohortKey ?? "cohort";
      const initialChildren = nodeSpec.initialChildren ?? [];
      data = ensureShortLabel({
        id: `ui:PatientGroup|cohort|${key}`,
        type: "PatientGroup",
        label: nodeSpec.summaryLabel || nodeSpec.label,
        expandable: initialChildren.length === 0,
        expanded: initialChildren.length > 0,
        context: {
          cohortFilters: nodeSpec.context?.filters ?? {},
          cohortKey: key,
        },
      });
    } else {
      data = ensureShortLabel({
        id: `ui:concept|${nodeSpec.conceptSystem}|${nodeSpec.conceptCode}`,
        type: "Concept",
        label: nodeSpec.label,
        expandable: true,
        context: {
          conceptSystem: nodeSpec.conceptSystem,
          conceptCode: nodeSpec.conceptCode,
        },
      });
    }

    cy.add({
      group: "nodes",
      data,
      position: { x: 0, y: 0 },
      classes: `${data.expandable ? "expandable " : ""}show-label`.trim(),
    });

    const node = cy.nodes()[0];

    if (nodeSpec.graphMode === "cohort" && nodeSpec.initialChildren?.length) {
      addChildNodes(cy, node, nodeSpec.initialChildren);
      await runExpandLayout(cy, node, nodeSpec.initialChildren.length);
    } else if (
      (nodeSpec.graphMode === "cohort"
        || nodeSpec.graphMode === "metric"
        || nodeSpec.graphMode === "concept")
      && nodeSpec.autoExpand !== false
      && data.expandable
    ) {
      await handleExpandRef.current?.(node);
    }

    cy.nodes().addClass("show-label");
    highlightNeighborhood(cy, node, { dimOthers: false });

    reportStats(cy);
    deferFit(cy, 80);
  }, [addChildNodes, reportStats]);

  useEffect(() => {
    if (!containerRef.current) return;

    const cy = Cytoscape({
      container: containerRef.current,
      style: getCytoscapeStyles(theme),
      ...CY_BASE_OPTIONS,
    });
    cyRef.current = cy;
    onCyReadyRef.current?.({
      cy,
      expandNode: (node) => handleExpandRef.current?.(node),
      collapseNode: (node) => handleCollapseRef.current?.(node),
      focusNode: (node) => {
        if (!node || node.empty()) return;
        cy.elements().removeClass("dimmed highlighted");
        highlightNeighborhood(cy, node, { dimOthers: true });
        node.select();
        onNodeSelectRef.current?.(node.data());
        cy.animate({ center: { eles: node }, zoom: Math.min(cy.maxZoom(), Math.max(cy.zoom(), 1.1)) }, { duration: 300 });
      },
      dismissNode: (node) => {
        if (!node || node.empty()) return;
        node.remove();
        onNodeSelectRef.current?.(null);
        reportStats(cy);
      },
    });

    cy.on("tap", "node", (evt) => {
      const node = evt.target;
      onNodeSelectRef.current?.(nodeSelectionPayload(node));
      highlightNeighborhood(cy, node, { dimOthers: true });
      reportStats(cy);
    });

    cy.on("dbltap", "node", (evt) => {
      handleExpandRef.current?.(evt.target);
    });

    cy.on("cxttap", "node", (evt) => {
      evt.originalEvent?.preventDefault();
      const node = evt.target;
      if (node.data("expanded")) {
        handleCollapseRef.current?.(node);
      }
    });

    cy.on("tap", (evt) => {
      if (evt.target === cy) {
        cy.elements().removeClass("dimmed highlighted show-label");
        cy.edges().removeClass("highlighted");
        onNodeSelectRef.current?.(null);
        setTooltip(null);
        reportStats(cy);
      }
    });

    cy.on("mouseover", "node", (evt) => {
      hoveredNodeRef.current = evt.target;
      updateTooltipForNode(evt.target);
    });

    cy.on("mouseout", "node", () => {
      hoveredNodeRef.current = null;
      setTooltip(null);
    });

    cy.on("pan zoom", () => {
      onZoomChangeRef.current?.(cy.zoom());
      if (hoveredNodeRef.current) {
        updateTooltipForNode(hoveredNodeRef.current);
      }
    });

    const resizeObserver = new ResizeObserver(() => {
      if (cy.destroyed()) return;
      cy.resize();
      if (cy.nodes().length > 0) {
        deferFit(cy, 80);
      }
    });
    resizeObserver.observe(containerRef.current);

    const preventContextMenu = (event) => event.preventDefault();
    containerRef.current.addEventListener("contextmenu", preventContextMenu);

    return () => {
      containerRef.current?.removeEventListener("contextmenu", preventContextMenu);
      resizeObserver.disconnect();
      cy.destroy();
      cyRef.current = null;
    };
  }, [updateTooltipForNode, reportStats]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || cy.destroyed()) return;
    cy.style(getCytoscapeStyles(theme));
  }, [theme]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || cy.destroyed() || !rootNode) return;
    loadRootNode(cy, rootNode);
  }, [rootNode, loadRootNode]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || cy.destroyed() || fitTrigger === 0) return;
    deferFit(cy, 80);
  }, [fitTrigger]);

  useEffect(() => {
    if (!visible) return;
    const cy = cyRef.current;
    if (!cy || cy.destroyed() || cy.nodes().length === 0) return;
    deferFit(cy, 80);
  }, [visible]);

  useEffect(() => {
    if (expandAllCancelTrigger === 0) return;
    expandAllCancelledRef.current = true;
    const cy = cyRef.current;
    clearExpandLoadingState(cy);
    onLoadingChangeRef.current?.(false);
  }, [expandAllCancelTrigger]);

  useEffect(() => {
    if (expandAllTrigger === 0) return;
    const cy = cyRef.current;
    if (!cy || cy.destroyed()) return;

    let cancelled = false;
    expandAllCancelledRef.current = false;
    expandAllActiveRef.current = true;
    onExpandAllActivityChangeRef.current?.(true);

    (async () => {
      onLoadingChangeRef.current?.(true);
      try {
        const expandable = cy
          .nodes()
          .filter((n) => n.data("expandable") && !n.data("expanded"));
        for (const node of expandable) {
          if (cancelled || expandAllCancelledRef.current) break;
          await handleExpandRef.current?.(node);
        }
        if (expandAllCancelledRef.current) {
          onExpandNoticeRef.current?.("Expand all cancelled.");
        }
        reportStats(cy);
      } finally {
        expandAllActiveRef.current = false;
        onExpandAllActivityChangeRef.current?.(false);
        clearExpandLoadingState(cy);
        onLoadingChangeRef.current?.(false);
      }
    })();

    return () => {
      cancelled = true;
      expandAllCancelledRef.current = true;
    };
  }, [expandAllTrigger, reportStats]);

  useEffect(() => {
    if (collapseAllTrigger === 0) return;
    const cy = cyRef.current;
    if (!cy || cy.destroyed() || !rootNode) return;
    loadRootNode(cy, rootNode);
  }, [collapseAllTrigger, rootNode, loadRootNode]);

  useEffect(() => {
    if (relayoutTrigger === 0) return;
    const cy = cyRef.current;
    if (!cy || cy.destroyed() || cy.nodes().length < 2) return;

    onLoadingChangeRef.current?.(true);
    runLayout(cy, layoutModeRef.current, null)
      .then(() => deferFit(cy, 80))
      .finally(() => onLoadingChangeRef.current?.(false));
  }, [relayoutTrigger, layoutMode]);

  const prevExpandLimitRef = useRef(expandLimit);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || cy.destroyed()) return;
    if (prevExpandLimitRef.current === expandLimit) return;
    prevExpandLimitRef.current = expandLimit;

    const candidates = cy.nodes().filter((node) => {
      const patients = getPatientChildren(node);
      return patients.length > 0 && patients.length < expandLimit;
    });

    if (candidates.length === 0) return;

    let cancelled = false;
    (async () => {
      onLoadingChangeRef.current?.(true);
      try {
        for (const node of candidates) {
          if (cancelled) break;
          await handleExpandRef.current?.(node);
        }
        reportStats(cy);
        deferFit(cy, 80);
      } finally {
        if (!cancelled) onLoadingChangeRef.current?.(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [expandLimit, reportStats]);

  return (
    <div className="graph-canvas-wrap">
      <div className="graph-hint-bar">
        <span>Click to select · Double-click or Expand to drill down · Right-click expanded node to collapse · Explore node for details</span>
      </div>
      <div ref={containerRef} className="graph-canvas" />
      {tooltip && (
        <div
          className="graph-tooltip"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          <span className="tooltip-type">{tooltip.type}</span>
          <p className="tooltip-label">{tooltip.label}</p>
          {tooltip.expandable && (
            <span className="tooltip-action">Double-click to expand</span>
          )}
          {tooltip.expanded && (
            <span className="tooltip-action">Right-click to collapse</span>
          )}
        </div>
      )}
    </div>
  );
}
