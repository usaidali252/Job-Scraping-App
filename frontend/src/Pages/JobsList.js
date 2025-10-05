// APP/frontend/src/Pages/JobsList.js
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { listJobs, deleteJob, startScrape, scrapeStatus } from "../api";
import { useNavigate } from "react-router-dom";
import ConfirmDialog from "../Components/ConfirmDialog";

const PAGE_BATCH = 50;

const initialFilters = {
  q: "",
  location: "",
  jobType: "",
  tags: [],
};

export default function JobsList() {
  const nav = useNavigate();
  const [filters, setFilters] = useState(initialFilters);
  const [sort, setSort] = useState("posting_date_desc");
  const [jobs, setJobs] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const [toast, setToast] = useState(null);
  const [confirm, setConfirm] = useState({ open: false, id: null });

  // scraping progress (server is source of truth)
  const [scrape, setScrape] = useState({ running: false, fetched: 0, limit: 0, error: null });

  const filterKey = useMemo(
    () =>
      JSON.stringify({
        q: filters.q || "",
        location: filters.location || "",
        jobType: filters.jobType || "",
        tags: (filters.tags || []).slice().sort(),
        sort,
      }),
    [filters.q, filters.location, filters.jobType, filters.tags, sort]
  );

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setErr("");
    try {
      const merged = [];
      let page = 1;
      let hasNext = true;
      let totalCount = 0;
      while (hasNext) {
        const res = await listJobs({
          page,
          pageSize: PAGE_BATCH,
          sort,
          q: filters.q || undefined,
          location: filters.location || undefined,
          jobType: filters.jobType || undefined,
          tags: filters.tags && filters.tags.length ? filters.tags : undefined,
        });
        merged.push(...(res.items || []));
        totalCount = res.total ?? merged.length;
        hasNext = !!(res.page_meta && res.page_meta.has_next);
        page += 1;
      }
      setJobs(merged);
      setTotal(totalCount);
    } catch (e) {
      setErr(e?.message || "Failed to fetch jobs");
    } finally {
      setLoading(false);
    }
  }, [filterKey, sort, filters]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // NEW: bootstrap scraper status on mount (so navigation/reload preserves UI state)
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const s = await scrapeStatus();
        if (!alive) return;
        setScrape(s.status || { running: false, fetched: 0, limit: 0, error: null });
      } catch (_) {
        // ignore
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  // poll scraper status if running
  useEffect(() => {
    if (!scrape.running) return;
    let alive = true;
    const tick = async () => {
      try {
        const s = await scrapeStatus();
        if (!alive) return;
        setScrape(s.status);
        if (!s.status.running) {
          setToast({ msg: `Fetched ${s.status.fetched} jobs.`, type: "info" });
          fetchAll();
        }
      } catch (_) {
        // ignore one-off poll failures
      }
    };
    const id = setInterval(tick, 1000);
    tick();
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [scrape.running, fetchAll]);

  const onChangeFilter = (key, value) => {
    setFilters((f) => ({
      ...f,
      [key]:
        key === "tags"
          ? Array.isArray(value)
            ? value
            : value.split(",").map((s) => s.trim()).filter(Boolean)
          : value,
    }));
  };

  const clearChip = (key, val) => {
    if (key === "tags") setFilters((f) => ({ ...f, tags: f.tags.filter((t) => t !== val) }));
    else setFilters((f) => ({ ...f, [key]: "" }));
  };

  const clearAll = () => {
    setFilters(initialFilters);
    setSort("posting_date_desc");
  };

  const askDelete = (id) => setConfirm({ open: true, id });
  const doDelete = async () => {
    const id = confirm.id;
    setConfirm({ open: false, id: null });
    try {
      await deleteJob(id);
      setJobs((prev) => prev.filter((j) => j.id !== id));
      setTotal((t) => Math.max(0, t - 1));
      setToast({ msg: "Job deleted" });
    } catch (e) {
      setToast({ msg: e?.message || "Failed to delete", type: "error" });
    }
  };

  const onFetchLatest = async () => {
    try {
      const s = await startScrape({ limit: 50 });
      setScrape(s.status || { running: true, fetched: 0, limit: 50, error: null });
      setToast({ msg: "Fetching latest jobs…" });
    } catch (e) {
      // If another tab/session already started it, backend returns 409.
      // Just sync status and resume polling.
      try {
        const s = await scrapeStatus();
        if (s?.status?.running) {
          setScrape(s.status);
          setToast({ msg: "Fetch already in progress — resuming…" });
          return;
        }
      } catch (_) {}
      setToast({ msg: e?.message || "Failed to start fetch", type: "error" });
    }
  };

  return (
    <div className="container">
      <div className="header">
        <h1>Job Listings</h1>
        <span className="sub">Actuarial roles from your backend</span>
      </div>

      <div className="panel">
        <div className="toolbar">
          <div className="filters">
            <input
              className="input"
              placeholder="Search keyword (title or company)…"
              value={filters.q}
              onChange={(e) => onChangeFilter("q", e.target.value)}
            />
            <input
              className="input"
              placeholder="Location (e.g., London, Remote)…"
              value={filters.location}
              onChange={(e) => onChangeFilter("location", e.target.value)}
            />
            <select
              className="select"
              value={filters.jobType}
              onChange={(e) => onChangeFilter("jobType", e.target.value)}
            >
              <option value="">All types</option>
              <option>Full-time</option>
              <option>Part-time</option>
              <option>Contract</option>
              <option>Internship</option>
            </select>
            <input
              className="input"
              placeholder="Tags (comma separated)"
              value={filters.tags.join(", ")}
              onChange={(e) => onChangeFilter("tags", e.target.value)}
            />
            <select className="select" value={sort} onChange={(e) => setSort(e.target.value)}>
              <option value="posting_date_desc">Date posted: Newest first</option>
              <option value="posting_date_asc">Date posted: Oldest first</option>
              <option value="title_asc">Title: A → Z</option>
              <option value="title_desc">Title: Z → A</option>
            </select>
          </div>

          <div className="toolbar-actions">
            <button className="btn ghost" onClick={clearAll} title="Clear all filters">
              Clear all
            </button>
            <button
              className="btn primary"
              onClick={onFetchLatest}
              title="Fetch latest jobs"
              disabled={scrape.running}
            >
              {scrape.running ? "Fetching…" : "Fetch latest"}
            </button>
          </div>

          {scrape.running ? (
            <div className="progress" aria-live="polite">
              <div
                className="progress-bar"
                style={{
                  width: `${Math.min(100, (scrape.fetched / (scrape.limit || 1)) * 100)}%`,
                }}
              />
              <div className="progress-text">
                Fetching… {scrape.fetched} / {scrape.limit || "?"}
              </div>
            </div>
          ) : null}
        </div>

        <div className="chips">
          {filters.q ? (
            <span className="chip">
              q: <strong>{filters.q}</strong>
              <button className="x" onClick={() => clearChip("q")}>
                ×
              </button>
            </span>
          ) : null}
          {filters.location ? (
            <span className="chip">
              location: <strong>{filters.location}</strong>
              <button className="x" onClick={() => clearChip("location")}>
                ×
              </button>
            </span>
          ) : null}
          {filters.jobType ? (
            <span className="chip">
              type: <strong>{filters.jobType}</strong>
              <button className="x" onClick={() => clearChip("jobType")}>
                ×
              </button>
            </span>
          ) : null}
          {(filters.tags || []).map((t) => (
            <span className="chip" key={t}>
              tag: <strong>{t}</strong>
              <button className="x" onClick={() => clearChip("tags", t)}>
                ×
              </button>
            </span>
          ))}
          <span className="count right">{loading ? "Loading…" : `${total} results`}</span>
        </div>
      </div>

      {err ? (
        <div className="center error">{err}</div>
      ) : loading ? (
        <div className="center">Loading jobs…</div>
      ) : jobs.length === 0 ? (
        <div className="center">No jobs found.</div>
      ) : (
        <div className="grid">
          {jobs.map((j) => (
            <div className="card" key={j.id}>
              <div className="title">{j.title}</div>
              <div className="meta">
                <span>🏢 {j.company}</span>
                {j.location ? <span>📍 {j.location}</span> : null}
                {j.job_type ? <span>💼 {j.job_type}</span> : null}
                {j.posting_date ? <span>📅 {j.posting_date}</span> : null}
              </div>
              {Array.isArray(j.tags) && j.tags.length ? (
                <div className="tags">{j.tags.map((t) => <span key={t} className="tag">{t}</span>)}</div>
              ) : null}
              {j.description ? (
                <div className="sub" style={{ marginTop: 8 }}>
                  {j.description.slice(0, 160)}
                  {j.description.length > 160 ? "…" : ""}
                </div>
              ) : null}
              <div className="actions">
                {j.source_url ? (
                  <a className="btn" href={j.source_url} target="_blank" rel="noreferrer">
                    View Post
                  </a>
                ) : null}
                <button className="btn" onClick={() => nav(`/edit/${j.id}`)}>
                  Edit
                </button>
                <button className="btn" onClick={() => askDelete(j.id)}>
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {toast ? (
        <div className={`toast ${toast.type === "error" ? "toast-error" : ""}`} role="status" aria-live="polite">
          {toast.msg}
        </div>
      ) : null}

      <ConfirmDialog
        open={confirm.open}
        title="Delete this job?"
        body="This action cannot be undone."
        onCancel={() => setConfirm({ open: false, id: null })}
        onConfirm={doDelete}
      />
    </div>
  );
}
