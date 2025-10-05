//frontend/src/component/JobCard.js
import { useNavigate } from "react-router-dom";
import DeleteJob from "./DeleteJob";

export default function JobCard({ job, onDeleted }) {
  const nav = useNavigate();
  return (
    <div className="card">
      <div className="title">{job.title}</div>
      <div className="sub">{job.company} • {job.location} • {job.job_type || "—"}</div>
      <div className="sub">Posted: {job.posting_date || "—"}</div>
      {job.tags?.length ? (
        <div className="tags">{job.tags.map(t => <span className="tag" key={t}>{t}</span>)}</div>
      ) : null}
      <div className="actions">
        <button className="btn" onClick={() => nav(`/edit/${job.id}`)}>Edit</button>
        <DeleteJob id={job.id} onDeleted={onDeleted} />
      </div>
    </div>
  );
}
