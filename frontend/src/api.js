const API_BASE = (process.env.REACT_APP_API_BASE || "http://localhost:5000").replace(/\/$/, "");
const API = `${API_BASE}/api`;

function toQuery(params = {}) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v == null || v === "" || (Array.isArray(v) && v.length === 0)) continue;
    if (Array.isArray(v)) v.forEach((x) => q.append(k, x));
    else q.set(k, v);
  }
  const qs = q.toString();
  return qs ? `?${qs}` : "";
}

export async function listJobs(options = {}) {
  const {
    page = 1, pageSize = 10, sort = "posting_date_desc",
    q, location, jobType, tags,
  } = options;

  const params = { page, page_size: pageSize, sort, q, location, job_type: jobType };
  if (Array.isArray(tags) && tags.length) params.tag = tags;

  const res = await fetch(`${API}/jobs${toQuery(params)}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getJob(id) {
  const res = await fetch(`${API}/jobs/${id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function createJob(payload) {
  const res = await fetch(`${API}/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (res.status === 201) return res.json();
  throw new Error(await res.text());
}

export async function updateJob(id, payload) {
  const res = await fetch(`${API}/jobs/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deleteJob(id) {
  const res = await fetch(`${API}/jobs/${id}`, { method: "DELETE" });
  if (res.status === 204) return true;
  throw new Error(await res.text());
}

// Scraper controls
export async function startScrape({ limit = 50 } = {}) {
  const res = await fetch(`${API}/scrape/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ limit, headless: true }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function scrapeStatus() {
  const res = await fetch(`${API}/scrape/status`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
