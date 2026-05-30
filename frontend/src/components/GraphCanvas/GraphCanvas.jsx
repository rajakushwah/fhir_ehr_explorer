import { useCallback, useEffect, useRef, useState } from "react";
import Cytoscape from "cytoscape";
import { expandNode } from "@/api/api";
import { getCytoscapeStyles } from "./graphStyles";
import {
  computeChildPositions,
  ensureShortLabel,
  registerFcose,
  runBloomLayout,
} from "./layout";

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

function highlightNeighborhood(cy, node) {
  cy.elements().removeClass("dimmed highlighted");
  cy.edges().removeClass("highlighted");
  if (!node || node.empty()) return;

  const hood = node.closedNeighborhood();
  cy.elements().not(hood).addClass("dimmed");
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

export default function GraphCanvas({
  rootNode,
  onNodeSelect,
  onStatsChange,
  onLoadingChange,
  fitTrigger,
  visible = true,
  onCyReady,
  theme = "dark",
}) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);
  const expandingRef = useRef(new Set());
  const hoveredNodeRef = useRef(null);
  const [tooltip, setTooltip] = useState(null);

  const onNodeSelectRef = useRef(onNodeSelect);
  const onCyReadyRef = useRef(onCyReady);
  const onStatsChangeRef = useRef(onStatsChange);
  const onLoadingChangeRef = useRef(onLoadingChange);
  onNodeSelectRef.current = onNodeSelect;
  onCyReadyRef.current = onCyReady;
  onStatsChangeRef.current = onStatsChange;
  onLoadingChangeRef.current = onLoadingChange;

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
    });
  }, []);

  const handleExpandRef = useRef(null);
  handleExpandRef.current = async (node) => {
    const cy = cyRef.current;
    if (!cy || !node?.data("expandable") || node.data("expanded")) return;
    if (expandingRef.current.has(node.id())) return;

    expandingRef.current.add(node.id());
    node.addClass("loading");
    onLoadingChangeRef.current?.(true);

    try {
      const result = await expandNode(node.data("type"), node.data("context"));
      const children = result.nodes ?? [];

      const parentPos = node.position();
      const positions = computeChildPositions(parentPos, children.length);

      cy.batch(() => {
        children.forEach((child, i) => {
          if (cy.getElementById(child.data.id).length) return;

          const data = ensureShortLabel(child.data);
          const pos = positions[i] ?? { x: parentPos.x + 140, y: parentPos.y };
          const classes = [];
          if (data.expandable) classes.push("expandable");
          if (data.expanded) classes.push("expanded");

          cy.add({
            group: "nodes",
            data,
            position: pos,
            classes: classes.join(" "),
          });

          cy.add({
            group: "edges",
            data: {
              id: `${node.id()}->${child.data.id}`,
              source: node.id(),
              target: child.data.id,
            },
          });
        });

        node.data("expanded", true);
        node.removeClass("loading");
        node.addClass("expanded");
      });

      await runBloomLayout(cy, node);

      cy.animate({
        fit: { eles: node.closedNeighborhood(), padding: 80 },
        duration: 400,
        easing: "ease-out-cubic",
      });

      onStatsChangeRef.current?.({
        nodes: cy.nodes().length,
        edges: cy.edges().length,
      });
    } catch (err) {
      node.removeClass("loading");
      if (import.meta.env.DEV) console.error("[Graph] expand failed", err);
    } finally {
      expandingRef.current.delete(node.id());
      onLoadingChangeRef.current?.(false);
    }
  };

  const loadRootNode = useCallback((cy, nodeSpec) => {
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
      classes: "expandable show-label",
    });

    const node = cy.nodes()[0];
    node.select();
    onNodeSelectRef.current?.(node.data());
    highlightNeighborhood(cy, node);

    onStatsChangeRef.current?.({ nodes: 1, edges: 0 });
    deferFit(cy, 80);
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;

    const cy = Cytoscape({
      container: containerRef.current,
      style: getCytoscapeStyles(theme),
      ...CY_BASE_OPTIONS,
    });
    cyRef.current = cy;
    onCyReadyRef.current?.(cy);

    cy.on("tap", "node", (evt) => {
      const node = evt.target;
      onNodeSelectRef.current?.(node.data());
      highlightNeighborhood(cy, node);
      cy.nodes().removeClass("show-label");
      node.addClass("show-label");
      node.neighborhood().nodes().addClass("show-label");
    });

    cy.on("dbltap", "node", (evt) => {
      handleExpandRef.current?.(evt.target);
    });

    cy.on("tap", (evt) => {
      if (evt.target === cy) {
        cy.elements().removeClass("dimmed highlighted show-label");
        cy.edges().removeClass("highlighted");
        onNodeSelectRef.current?.(null);
        setTooltip(null);
      }
    });

    cy.on("mouseover", "node", (evt) => {
      const node = evt.target;
      hoveredNodeRef.current = node;
      node.addClass("show-label");
      updateTooltipForNode(node);
    });

    cy.on("mouseout", "node", (evt) => {
      hoveredNodeRef.current = null;
      if (!evt.target.selected()) {
        evt.target.removeClass("show-label");
      }
      setTooltip(null);
    });

    cy.on("pan zoom", () => {
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

    return () => {
      resizeObserver.disconnect();
      cy.destroy();
      cyRef.current = null;
    };
  }, [updateTooltipForNode]);

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

  return (
    <div className="graph-canvas-wrap">
      <div className="graph-hint-bar">
        <span>Click to select</span>
        <span className="hint-dot">·</span>
        <span>Double-click to expand</span>
        <span className="hint-dot">·</span>
        <span>Scroll to zoom</span>
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
        </div>
      )}
    </div>
  );
}
