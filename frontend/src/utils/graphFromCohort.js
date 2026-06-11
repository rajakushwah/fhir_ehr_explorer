const GROUP_NODE_TYPE = {
  gender: "Gender",
  state: "Region",
  city: "Region",
};

function capitalize(value) {
  if (!value) return value;
  const text = String(value);
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function canVisualizeCohort(result) {
  if (!result) return false;
  if (result.queryType === "aggregation" && result.aggregation) {
    return (result.aggregation.rows?.length ?? 0) > 0;
  }
  return (result.total ?? 0) > 0 || (result.totalMatched ?? 0) > 0;
}

function buildGroupedChildren(aggregation, graphContext) {
  const groupBy = aggregation.groupBy;
  if (!groupBy || aggregation.rows.length <= 1) return [];

  const nodeType = GROUP_NODE_TYPE[groupBy] ?? "Gender";
  const cohortKey = graphContext.cohortKey;
  const filters = graphContext.filters ?? {};

  return aggregation.rows.map((row) => {
    const context = {
      cohortFilters: filters,
      cohortKey,
    };

    if (groupBy === "gender") {
      context.gender = String(row.label).toLowerCase();
    } else if (groupBy === "state") {
      context.state = row.label;
    } else if (groupBy === "city") {
      context.city = row.label;
    }

    const display = capitalize(row.label);
    const count = Number(row.value).toLocaleString();

    const nodeLabel = `${display}\n(${count})`;

    return {
      id: `ui:${nodeType}|${row.label}|cohort|${cohortKey}`,
      type: nodeType,
      label: nodeLabel,
      shortLabel: nodeLabel,
      fullLabel: `${display} (${count})`,
      expandable: true,
      expanded: false,
      context,
    };
  });
}

export function buildGraphFromCohort(result) {
  if (!canVisualizeCohort(result)) return null;

  const graphContext = result.graphContext;
  if (!graphContext?.cohortKey) return null;

  if (result.concept && result.queryType !== "aggregation") {
    const total = result.totalMatched ?? result.total ?? 0;
    if (total > 0) {
      return {
        graphMode: "cohort",
        label: result.interpretation,
        summaryLabel: `${result.concept.label} · Patients (${Number(total).toLocaleString()})`,
        total,
        context: graphContext,
        initialChildren: [],
      };
    }
    return {
      graphMode: "concept",
      conceptSystem: result.concept.conceptSystem,
      conceptCode: result.concept.conceptCode,
      label: result.concept.label,
    };
  }

  if (result.queryType === "aggregation" && result.aggregation) {
    const { aggregation } = result;
    const isGrouped = aggregation.rows.length > 1;
    const total = result.totalMatched ?? result.total ?? 0;

    if (aggregation.target !== "Patient") {
      const value = aggregation.rows[0]?.value ?? total;
      return {
        graphMode: "metric",
        nodeType: aggregation.target,
        label: `${capitalize(aggregation.target)} (${Number(value).toLocaleString()})`,
        context: graphContext,
      };
    }

    return {
      graphMode: "cohort",
      label: result.interpretation,
      summaryLabel: isGrouped
        ? `Patients (${Number(total).toLocaleString()})`
        : aggregation.summary,
      total,
      context: graphContext,
      initialChildren: isGrouped ? buildGroupedChildren(aggregation, graphContext) : [],
    };
  }

  const total = result.totalMatched ?? result.total ?? 0;
  return {
    graphMode: "cohort",
    label: result.interpretation,
    summaryLabel: `Patients (${Number(total).toLocaleString()})`,
    total,
    context: graphContext,
    initialChildren: [],
  };
}
