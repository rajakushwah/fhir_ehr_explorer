const BASE_URL = import.meta.env.VITE_API_URL ?? "";

function logApi(level, message, detail = {}) {
  if (!import.meta.env.DEV) return;

  const suffix = Object.keys(detail).length
    ? ` | ${JSON.stringify(detail)}`
    : "";

  console[level](`[EHR Explorer] ${message}${suffix}`);
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
      const text = await res.text().catch(() => "");
      logApi("error", `${label} ✗ failed`, {
        status: res.status,
        ms: Math.round(ms),
        body: text.slice(0, 200),
      });
      throw new Error(`${label} failed (${res.status})`);
    }

    const data = await res.json();
    const count = Array.isArray(data) ? data.length : data.nodes?.length ?? 0;

    logApi("info", `${label} ✓ ok`, {
      ms: Math.round(ms),
      count,
    });

    return data;
  } catch (err) {
    const ms = performance.now() - t0;
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

export async function expandNode(nodeType, context) {
  return request(
    "/graph/expand",
    { nodeType, context },
    `expand/${nodeType}`
  );
}

export async function searchCohort(payload) {
  return request("/cohort/search", payload, "cohort/search");
}

export async function getCohortFilters() {
  const t0 = performance.now();
  try {
    const res = await fetch(`${BASE_URL}/cohort/filters`);
    if (!res.ok) throw new Error("Failed to load filters");
    return res.json();
  } catch (err) {
    logApi("error", "cohort/filters ✗", { error: err.message, ms: Math.round(performance.now() - t0) });
    throw err;
  }
}

export async function checkHealth() {
  const t0 = performance.now();
  try {
    const res = await fetch(`${BASE_URL}/health`);
    logApi("debug", "health ✓", {
      ms: Math.round(performance.now() - t0),
      ok: res.ok,
    });
    return res.ok;
  } catch (err) {
    logApi("warn", "health ✗ offline", {
      ms: Math.round(performance.now() - t0),
      error: err.message,
    });
    return false;
  }
}
