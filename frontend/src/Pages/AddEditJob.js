import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { createJob, getJob, updateJob } from "../api";
import { useToast } from "../Components/ToastProvider";

export default function AddEditJob({ mode }) {
  const { show, showError } = useToast();
  const isEdit = mode === "edit";
  const { id } = useParams();
  const nav = useNavigate();

  const [form, setForm] = useState({
    title: "", company: "", location: "",
    job_type: "Full-time", posting_date: "", tags: [], salary_text: "", description: ""
  });
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    async function load() {
      if (!isEdit) return;
      const j = await getJob(id);
      setForm({
        title: j.title || "",
        company: j.company || "",
        location: j.location || "",
        job_type: j.job_type || "Full-time",
        posting_date: j.posting_date || "",
        tags: j.tags || [],
        salary_text: j.salary_text || "",
        description: j.description || "",
      });
    }
    load().catch(() => {});
  }, [id, isEdit]);

  function set(k, v) { setForm(f => ({ ...f, [k]: v })); }
  function validate() {
    const e = {};
    if (!form.title?.trim()) e.title = "Title is required";
    if (!form.company?.trim()) e.company = "Company is required";
    if (!form.location?.trim()) e.location = "Location is required";
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function onSubmit(e) {
    e.preventDefault();
    if (!validate()) return;
    setBusy(true);
    try {
      const payload = {
        title: form.title.trim(),
        company: form.company.trim(),
        location: form.location.trim(),
        job_type: form.job_type || "Full-time",
        posting_date: form.posting_date || null,
        tags: form.tags,
        salary_text: form.salary_text || null,
        description: form.description?.trim() || null,
      };
      if (isEdit) {
        await updateJob(id, payload);
        show("Job updated");
      } else {
        await createJob(payload);
        show("Job added");
      }
      nav("/");
    } catch (err) {
      showError("Failed to save job");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h2>{isEdit ? "Edit Job" : "Add Job"}</h2>

      <form className="form" onSubmit={onSubmit}>
        <div className="row">
          <input className="input" placeholder="Title *" value={form.title} required
                 onChange={e => set("title", e.target.value)} />
          <input className="input" placeholder="Company *" value={form.company} required
                 onChange={e => set("company", e.target.value)} />
        </div>
        {errors.title && <div className="err">{errors.title}</div>}
        {errors.company && <div className="err">{errors.company}</div>}

        <div className="row">
          <input className="input" placeholder="Location *" value={form.location} required
                 onChange={e => set("location", e.target.value)} />
          <select className="select" value={form.job_type} onChange={e => set("job_type", e.target.value)}>
            <option>Full-time</option><option>Part-time</option>
            <option>Contract</option><option>Internship</option>
          </select>
        </div>
        {errors.location && <div className="err">{errors.location}</div>}

        <div className="row">
          <input className="input" type="date" value={form.posting_date || ""} onChange={e => set("posting_date", e.target.value)} />
          <input className="input" placeholder="Salary text (optional)" value={form.salary_text}
                 onChange={e => set("salary_text", e.target.value)} />
        </div>

        <textarea className="input" rows={6} placeholder="Description (optional)" value={form.description}
                  onChange={e => set("description", e.target.value)} />

        <input className="input" placeholder="Tags (comma separated)" value={(form.tags || []).join(", ")}
               onChange={e => set("tags", e.target.value.split(",").map(s => s.trim()).filter(Boolean))} />

        <button className="btn primary" disabled={busy}>{isEdit ? "Save Changes" : "Add Job"}</button>
      </form>
    </>
  );
}
