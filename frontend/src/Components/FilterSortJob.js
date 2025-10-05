//frontend/src/component/FilterSortJob.js
import { useEffect, useState } from "react";

export default function FilterSortJob({ value, onChange }) {
  const [local, setLocal] = useState(value || { q:"", location:"", job_type:"", tags:[], sort:"posting_date_desc" });

  useEffect(()=>{ setLocal(value); }, [value]);

  function set(k, v){ const next = {...local, [k]:v}; setLocal(next); onChange(next); }

  return (
    <div className="controls">
      <input className="input" placeholder="Search title or company" value={local.q||""}
             onChange={e=>set("q", e.target.value)} />
      <input className="input" placeholder="Location" value={local.location||""}
             onChange={e=>set("location", e.target.value)} />
      <select className="select" value={local.job_type||""} onChange={e=>set("job_type", e.target.value)}>
        <option value="">All types</option>
        <option>Full-time</option><option>Part-time</option>
        <option>Contract</option><option>Internship</option>
      </select>
      <input className="input" placeholder="Tags (comma separated)"
             value={(local.tags||[]).join(", ")}
             onChange={e=>set("tags", e.target.value.split(",").map(s=>s.trim()).filter(Boolean))}/>
      <select className="select" value={local.sort||"posting_date_desc"} onChange={e=>set("sort", e.target.value)}>
        <option value="posting_date_desc">Date Posted: Newest First</option>
        <option value="posting_date_asc">Date Posted: Oldest First</option>
        <option value="title_asc">Title: A → Z</option>
        <option value="title_desc">Title: Z → A</option>
      </select>
      <button className="btn" onClick={()=>onChange({q:"",location:"",job_type:"",tags:[],sort:"posting_date_desc"})}>Reset</button>
    </div>
  );
}
