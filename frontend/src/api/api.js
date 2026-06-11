const BASE_URL = import.meta.env.VITE_API_URL ?? "";

function logApi(level, message, detail = {}) {
  if (!import.meta.env.DEV) return;

  const suffix = Object.keys(detail).length
    ? ` | ${JSON.stringify(detail)}`
    : "";

  console[level](`[EHR Explorer] ${message}${suffix}`);
}

async function parseErrorResponse(res) {
  const text = await res.text().catch(() => "");
  try {
    const json = JSON.parse(text);
    if (typeof json.detail === "string") return json.detail;
    if (Array.isArray(json.detail)) {
      return json.detail.map((d) => d.msg ?? JSON.stringify(d)).join("; ");
    }
  } catch {
    // not JSON
  }
  return text || `Request failed (${res.status})`;
}

async function request(path, body, label) {
  const t0 = performance.now();

  logApi("info", `${label} → started`, body);

  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const ms = performance.now() - t0;

    if (!res.ok) {
      const detail = await parseErrorResponse(res);
      logApi("error", `${label} ✗ failed`, {
        status: res.status,
        ms: Math.round(ms),
        detail,
      });
      throw new Error(detail);
    }

    const data = await res.json();
    const count = Array.isArray(data) ? data.length : data.nodes?.length ?? data.total ?? 0;

    logApi("info", `${label} ✓ ok`, {
      ms: Math.round(ms),
      count,
    });

    return data;
  } catch (err) {
    const ms = performance.now() - t0;
    if (err instanceof TypeError && err.message.includes("fetch")) {
      const msg = "Cannot reach backend API. Is the server running on port 8002?";
      logApi("error", `${label} ✗ offline`, { ms: Math.round(ms), error: msg });
      throw new Error(msg);
    }
    if (!(err instanceof Error && err.message.includes("failed"))) {
      logApi("error", `${label} ✗ error`, {
        ms: Math.round(ms),
        error: err.message,
      });
    }
    throw err;
  }
}

export async function searchConcepts(query) {
  if (!query?.trim()) return [];
  return request("/search", { query: query.trim() }, "search");
}

export async function expandNode(nodeType, context, limit) {
  const body = { nodeType, context };
  if (limit != null) {
    body.limit = limit;
  }
  return request("/graph/expand", body, `expand/${nodeType}`);
}

export async function getNodeDetail(nodeType, context, meta) {
  return request("/graph/node/detail", { nodeType, context, meta }, `node/detail/${nodeType}`);
}

export async function getNodeNeighbors(nodeType, context, filterType, limit = 50) {
  return request(
    "/graph/node/neighbors",
    { nodeType, context, filterType, limit },
    `node/neighbors/${nodeType}`
  );
}

export async function getNodeRelationships(nodeType, context, filterRel, limit = 50) {
  return request(
    "/graph/node/relationships",
    { nodeType, context, filterRel, limit },
    `node/relationships/${nodeType}`
  );
}

export async function searchCohort(payload) {
  return request("/cohort/search", payload, "cohort/search");
}

export async function getCohortFilters() {
  const t0 = performance.now();
  try {
    const res = await fetch(`${BASE_URL}/cohort/filters`);
    if (!res.ok) {
      const detail = await parseErrorResponse(res);
      throw new Error(detail);
    }
    return res.json();
  } catch (err) {
    if (err instanceof TypeError) {
      throw new Error("Cannot reach backend API. Is the server running on port 8002?");
    }
    logApi("error", "cohort/filters ✗", {
      error: err.message,
      ms: Math.round(performance.now() - t0),
    });
    throw err;
  }
}

export async function checkHealth() {
  const t0 = performance.now();
  try {
    const res = await fetch(`${BASE_URL}/health`);
    if (!res.ok) {
      return {
        backendOnline: false,
        neo4jOnline: false,
        status: "offline",
        neo4jError: "Backend API is not responding.",
      };
    }
    const data = await res.json();
    logApi("debug", "health", {
      ms: Math.round(performance.now() - t0),
      ...data,
    });
    return {
      backendOnline: true,
      neo4jOnline: Boolean(data.neo4j),
      status: data.status ?? "ok",
      neo4jError: data.neo4jError ?? null,
    };
  } catch (err) {
    logApi("warn", "health ✗ offline", {
      ms: Math.round(performance.now() - t0),
      error: err.message,
    });
    return {
      backendOnline: false,
      neo4jOnline: false,
      status: "offline",
      neo4jError: "Cannot reach backend API. Is the server running on port 8002?",
    };
  }
}
