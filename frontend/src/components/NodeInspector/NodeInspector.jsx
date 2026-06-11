import { useCallback, useEffect, useMemo, useState } from "react";
import { getNodeDetail, getNodeNeighbors, getNodeRelationships } from "@/api/api";
import { getNodeTypeColor } from "@/components/GraphCanvas/layout";

const TABS = ["Properties", "Neighbors", "Relationships"];

function formatValue(value) {
  if (value == null || value === "") return "—";
  const str = String(value);
  if (/^\d{4}-\d{2}-\d{2}T/.test(str)) {
    try {
      return new Date(str).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      });
    } catch {
      return str;
    }
  }
  return str;
}

function TypeBadge({ type }) {
  const color = getNodeTypeColor(type);
  return (
    <span className="bloom-type-badge" style={{ backgroundColor: color }}>
      {type}
    </span>
  );
}

function FilterChips({ items, active, onSelect, allCount }) {
  return (
    <div className="bloom-filter-row">
      <span className="bloom-filter-icon" aria-hidden>
        ⛃
      </span>
      <div className="bloom-filter-chips">
        <button
          type="button"
          className={`bloom-chip${active === null ? " is-active" : ""}`}
          onClick={() => onSelect(null)}
        >
          All {allCount}
        </button>
        {items.map(({ key, label, count }) => (
          <button
            key={key}
            type="button"
            className={`bloom-chip${active === key ? " is-active" : ""}`}
            onClick={() => onSelect(key)}
            title={label}
          >
            {label} {count}
          </button>
        ))}
      </div>
    </div>
  );
}

function PropertiesTab({ properties, loading }) {
  if (loading) {
    return <p className="bloom-tab-empty">Loading properties…</p>;
  }
  const entries = Object.entries(properties || {});
  if (entries.length === 0) {
    return <p className="bloom-tab-empty">No properties available.</p>;
  }
  return (
    <div className="bloom-properties">
      <div className="bloom-properties-toolbar">
        <button type="button" className="bloom-edit-btn" disabled title="Read-only view">
          ✎ Edit
        </button>
      </div>
      <dl className="bloom-prop-table">
        {entries.map(([key, value]) => (
          <div key={key} className="bloom-prop-row">
            <dt>{key}</dt>
            <dd>{formatValue(value)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function NeighborsTab({
  summary,
  neighbors,
  loading,
  filterType,
  onFilterType,
  onJump,
  onReveal,
}) {
  const allCount = summary.reduce((n, s) => n + s.count, 0);
  const chips = summary.map((s) => ({
    key: s.type,
    label: s.type,
    count: s.count,
  }));

  return (
    <>
      <FilterChips
        items={chips}
        active={filterType}
        onSelect={onFilterType}
        allCount={allCount}
      />
      {loading ? (
        <p className="bloom-tab-empty">Loading neighbors…</p>
      ) : neighbors.length === 0 ? (
        <p className="bloom-tab-empty">No neighbors found.</p>
      ) : (
        <ul className="bloom-neighbor-list">
          {neighbors.map((n, i) => (
            <li key={`${n.key}-${n.rel}-${i}`} className="bloom-neighbor-card">
              <div className="bloom-neighbor-left">
                <span className="bloom-neighbor-key">{n.key.slice(0, 8)}…</span>
                <TypeBadge type={n.nodeType} />
              </div>
              <div className="bloom-neighbor-props">
                {Object.entries(n.properties || {})
                  .slice(0, 4)
                  .map(([k, v]) => (
                    <div key={k} className="bloom-neighbor-prop">
                      <span>{k}</span>
                      <span>{formatValue(v)}</span>
                    </div>
                  ))}
              </div>
              <div className="bloom-neighbor-actions">
                <button type="button" onClick={() => onJump?.(n)} title="Jump to node">
                  ⊙ Jump
                </button>
                <button type="button" onClick={() => onReveal?.(n)} title="Reveal in graph">
                  ⎇ Reveal
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function RelationshipsTab({
  summary,
  relationships,
  loading,
  filterRel,
  onFilterRel,
}) {
  const allCount = summary.reduce((n, s) => n + s.count, 0);
  const chips = summary.map((s) => ({
    key: s.rel,
    label: s.rel,
    count: s.count,
  }));

  return (
    <>
      <FilterChips
        items={chips}
        active={filterRel}
        onSelect={onFilterRel}
        allCount={allCount}
      />
      {loading ? (
        <p className="bloom-tab-empty">Loading relationships…</p>
      ) : relationships.length === 0 ? (
        <p className="bloom-tab-empty">No relationships found.</p>
      ) : (
        <ul className="bloom-rel-list">
          {relationships.map((r, i) => (
            <li key={`${r.rel}-${r.sourceKey}-${r.targetKey}-${i}`} className="bloom-rel-row">
              <div className="bloom-rel-end">
                <span className="bloom-rel-key">{r.sourceKey.slice(0, 8)}…</span>
                <TypeBadge type={r.sourceType} />
              </div>
              <div className="bloom-rel-center">
                <strong>{r.rel}</strong>
                <span className="bloom-rel-arrow">→</span>
              </div>
              <div className="bloom-rel-end bloom-rel-end-target">
                <span className="bloom-rel-key">{r.targetKey.slice(0, 8)}…</span>
                <TypeBadge type={r.targetType} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

export default function NodeInspector({
  node,
  cy,
  onClose,
  onFocusNode,
  onRevealNode,
  onDismissNode,
  onCollapseNode,
}) {
  const [tab, setTab] = useState("Properties");
  const [detail, setDetail] = useState(null);
  const [neighbors, setNeighbors] = useState([]);
  const [relationships, setRelationships] = useState([]);
  const [filterType, setFilterType] = useState(null);
  const [filterRel, setFilterRel] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [loadingNeighbors, setLoadingNeighbors] = useState(false);
  const [loadingRels, setLoadingRels] = useState(false);

  const nodeType = node?.type;
  const context = node?.context ?? {};
  const meta = node?.meta ?? {};

  const canvasNeighbors = useMemo(() => {
    if (!cy || !node?.id) return { summary: [], items: [] };
    const el = cy.getElementById(node.id);
    if (!el.length) return { summary: [], items: [] };

    const byType = {};
    const items = [];
    el.connectedEdges().forEach((edge) => {
      const other = edge.source().id() === node.id ? edge.target() : edge.source();
      const type = other.data("type");
      byType[type] = (byType[type] || 0) + 1;
      items.push({
        nodeType: type,
        rel: edge.data("relType") || "RELATED_TO",
        direction: edge.source().id() === node.id ? "out" : "in",
        label: other.data("fullLabel") || other.data("label"),
        key: other.id(),
        properties: { ...(other.data("meta") || {}), ...(other.data("context") || {}) },
        cyNode: other,
      });
    });
    const summary = Object.entries(byType)
      .map(([type, count]) => ({ type, count }))
      .sort((a, b) => b.count - a.count);
    return { summary, items };
  }, [cy, node?.id]);

  useEffect(() => {
    if (!node) return;
    setTab("Properties");
    setFilterType(null);
    setFilterRel(null);
    setLoadingDetail(true);
    const ctx = node.context ?? {};
    const nodeMeta = node.meta ?? {};
    getNodeDetail(node.type, ctx, nodeMeta)
      .then(setDetail)
      .catch(() => setDetail({ properties: { ...nodeMeta, ...ctx }, fromDatabase: false }))
      .finally(() => setLoadingDetail(false));
  }, [node?.id]);

  useEffect(() => {
    if (!node || tab !== "Neighbors") return;
    setLoadingNeighbors(true);
    const ctx = node.context ?? {};
    getNodeNeighbors(node.type, ctx, filterType, 50)
      .then((res) => setNeighbors(res.neighbors || []))
      .catch(() => {
        const filtered = filterType
          ? canvasNeighbors.items.filter((n) => n.nodeType === filterType)
          : canvasNeighbors.items;
        setNeighbors(filtered);
      })
      .finally(() => setLoadingNeighbors(false));
  }, [node?.id, tab, filterType, canvasNeighbors.items]);

  useEffect(() => {
    if (!node || tab !== "Relationships") return;
    setLoadingRels(true);
    const ctx = node.context ?? {};
    getNodeRelationships(node.type, ctx, filterRel, 50)
      .then((res) => setRelationships(res.relationships || []))
      .catch(() => setRelationships([]))
      .finally(() => setLoadingRels(false));
  }, [node?.id, tab, filterRel]);

  const neighborSummary = detail?.fromDatabase
    ? detail.neighborSummary
    : canvasNeighbors.summary;

  const relSummary = detail?.relationshipSummary || [];

  const displayTitle = useMemo(() => {
    if (detail?.properties?.fhirId) return detail.properties.fhirId;
    if (context.patientFhirId) return context.patientFhirId;
    return node?.label || node?.id || "Node";
  }, [detail, context, node]);

  const handleJump = useCallback(
    (neighbor) => {
      if (neighbor.cyNode) {
        onFocusNode?.(neighbor.cyNode);
        return;
      }
      const cyNode = cy?.nodes().filter((n) => {
        const ctx = n.data("context") || {};
        return ctx.patientFhirId === neighbor.key || n.id().includes(neighbor.key);
      })[0];
      if (cyNode?.length) onFocusNode?.(cyNode);
    },
    [cy, onFocusNode]
  );

  if (!node) return null;

  return (
    <div className="bloom-inspector" role="dialog" aria-label="Node inspector">
      <header className="bloom-inspector-header">
        <TypeBadge type={nodeType} />
        <h2 className="bloom-inspector-title" title={displayTitle}>
          {displayTitle}
        </h2>
        <button type="button" className="bloom-inspector-close" onClick={onClose} aria-label="Close">
          ×
        </button>
      </header>

      <nav className="bloom-tabs">
        {TABS.map((name) => (
          <button
            key={name}
            type="button"
            className={`bloom-tab${tab === name ? " is-active" : ""}`}
            onClick={() => setTab(name)}
          >
            {name}
          </button>
        ))}
      </nav>

      <div className="bloom-inspector-body">
        {tab === "Properties" && (
          <PropertiesTab properties={detail?.properties} loading={loadingDetail} />
        )}
        {tab === "Neighbors" && (
          <NeighborsTab
            summary={neighborSummary}
            neighbors={neighbors}
            loading={loadingNeighbors}
            filterType={filterType}
            onFilterType={setFilterType}
            onJump={handleJump}
            onReveal={onRevealNode}
          />
        )}
        {tab === "Relationships" && (
          <RelationshipsTab
            summary={relSummary}
            relationships={relationships}
            loading={loadingRels}
            filterRel={filterRel}
            onFilterRel={setFilterRel}
          />
        )}
      </div>

      <footer className="bloom-inspector-footer">
        <button
          type="button"
          className="bloom-footer-btn"
          onClick={() => {
            const el = cy?.getElementById(node.id);
            if (el?.length) onFocusNode?.(el);
          }}
        >
          ⊙ Jump to node
        </button>
        <button
          type="button"
          className="bloom-footer-btn"
          onClick={() => {
            const el = cy?.getElementById(node.id);
            if (el?.length) onRevealNode?.(el);
          }}
        >
          ⎇ Reveal
        </button>
        {node.expanded && (
          <button
            type="button"
            className="bloom-footer-btn bloom-footer-btn-collapse"
            onClick={() => {
              const el = cy?.getElementById(node.id);
              if (el?.length) onCollapseNode?.(el);
            }}
          >
            ⊟ Collapse
          </button>
        )}
        <button
          type="button"
          className="bloom-footer-btn"
          onClick={() => {
            const el = cy?.getElementById(node.id);
            if (el?.length) onDismissNode?.(el);
            onClose?.();
          }}
        >
          ⊘ Dismiss
        </button>
      </footer>
    </div>
  );
}
