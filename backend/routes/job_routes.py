from contextlib import contextmanager
from dateutil import parser as dateparser
from flask import Blueprint, request, jsonify
from sqlalchemy import select, func, exists, cast, Date  # ← added cast, Date
from sqlalchemy.exc import IntegrityError

from db import SessionLocal
from models.job import Job, Tag, JobTag

job_bp = Blueprint("job_bp", __name__)

@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def _parse_tags_arg(arg_value):
    if not arg_value:
        return []
    if isinstance(arg_value, list):
        values = []
        for v in arg_value:
            values.extend([s.strip() for s in str(v).split(",") if s.strip()])
    else:
        values = [s.strip() for s in str(arg_value).split(",") if s.strip()]
    return [Tag.normalize(t) for t in values]

def _ensure_tags(session, tag_names: list[str]) -> list[Tag]:
    if not tag_names:
        return []
    normalized = [Tag.normalize(t) for t in tag_names if Tag.normalize(t)]
    if not normalized:
        return []
    existing = session.execute(select(Tag).where(Tag.name.in_(normalized))).scalars().all()
    existing_map = {t.name: t for t in existing}
    to_create = [n for n in normalized if n not in existing_map]
    created = []
    for n in to_create:
        t = Tag(name=n)
        session.add(t)
        created.append(t)
    session.flush()
    return list(existing_map.values()) + created

def _validate_job_payload(payload: dict, is_update: bool = False):
    errors = {}
    def req(field):
        if not payload.get(field):
            errors[field] = f"{field} is required."
    if not is_update:
        req("title")
        req("company")
        req("location")
    if "posting_date" in payload and payload["posting_date"]:
        try:
            dateparser.isoparse(payload["posting_date"]).date()
        except Exception:
            errors["posting_date"] = "posting_date must be ISO date, e.g., 2025-10-04"
    return errors

def _parse_posted_at(val: str | None):
    if not val:
        return None
    try:
        dt = dateparser.isoparse(val)
        if not dt.tzinfo:
            from datetime import timezone
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None

def _apply_filters_sort(query, args):
    q = args.get("q", type=str)
    location = args.get("location", type=str)
    job_type = args.get("job_type", type=str)
    tags = _parse_tags_arg(args.getlist("tag"))

    if q:
        like = f"%{q.lower()}%"
        query = query.where(
            func.lower(Job.title).like(like) | func.lower(Job.company).like(like)
        )

    # contains (case-insensitive)
    if location:
        like = f"%{location.strip().lower()}%"
        query = query.where(func.lower(Job.location).like(like))

    if job_type:
        query = query.where(func.lower(Job.job_type) == job_type.strip().lower())

    for t in tags:
        tag_exists = exists(
            select(JobTag.job_id)
            .join(Tag, Tag.id == JobTag.tag_id)
            .where(JobTag.job_id == Job.id, func.lower(Tag.name) == t)
        )
        query = query.where(tag_exists)

    # -------- Stable, sensible sort ----------
    # Use COALESCE(posting_date, posted_at::date, created_at::date)
    posted_sort_column = func.coalesce(
        Job.posting_date,
        cast(Job.posted_at, Date),
        cast(Job.created_at, Date),
    )

    sort = (args.get("sort") or "posting_date_desc").strip().lower()
    order_map = {
        "posting_date_desc": (Job.posting_date.desc().nullslast(), Job.created_at.desc()),
        "posting_date_asc":  (Job.posting_date.asc().nullsfirst(), Job.created_at.asc()),
        "title_asc":         (Job.title.asc(), Job.created_at.desc()),
        "title_desc":        (Job.title.desc(), Job.created_at.desc()),
    }
    ord_spec = order_map.get(sort, (Job.posting_date.desc().nullslast(), Job.created_at.desc()))
    if isinstance(ord_spec, tuple):
        return query.order_by(*ord_spec)
    return query.order_by(ord_spec)

    # ----------------------------------------

def _paginate(args, default_size: int, max_size: int):
    page = max(1, args.get("page", default=1, type=int) or 1)
    page_size = args.get("page_size", default=default_size, type=int) or default_size
    page_size = max(1, min(page_size, max_size))
    return page, page_size

@job_bp.get("/jobs")
def list_jobs():
    from config import Config
    with session_scope() as s:
        base = select(Job)
        base = _apply_filters_sort(base, request.args)
        count_subq = base.order_by(None).subquery()
        total = s.execute(select(func.count()).select_from(count_subq)).scalar_one()
        page, page_size = _paginate(request.args, Config.PAGINATION_DEFAULT_PAGE_SIZE, Config.PAGINATION_MAX_PAGE_SIZE)
        rows = s.execute(base.offset((page - 1) * page_size).limit(page_size)).unique().scalars().all()
        pages = (total + page_size - 1) // page_size
        return jsonify({
            "items": [j.to_dict() for j in rows],
            "page": page,
            "page_size": page_size,
            "total": total,
            "page_meta": {
                "pages": pages,
                "has_prev": page > 1,
                "has_next": page < pages,
                "prev_page": page - 1 if page > 1 else None,
                "next_page": page + 1 if page < pages else None,
            },
        })

@job_bp.get("/jobs/<int:job_id>")
def get_job(job_id: int):
    with session_scope() as s:
        job = s.get(Job, job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        return jsonify(job.to_dict())

@job_bp.post("/jobs")
def create_job():
    payload = request.get_json(silent=True) or {}
    errors = _validate_job_payload(payload, is_update=False)
    if errors:
        return jsonify({"error": errors}), 400
    with session_scope() as s:
        job = Job(
            title=payload.get("title", "").strip(),
            company=payload.get("company", "").strip(),
            location=payload.get("location", "").strip(),
            description=payload.get("description") or None,
            job_type=payload.get("job_type"),
            salary_text=payload.get("salary_text"),
            source_url=(payload.get("source_url") or None),
        )
        pd = payload.get("posting_date")
        if pd:
            job.posting_date = dateparser.isoparse(pd).date()
        pa = _parse_posted_at(payload.get("posted_at"))
        if pa:
            job.posted_at = pa
        tags = payload.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        job.tags = _ensure_tags(s, tags)
        s.add(job)
        try:
            s.flush()
        except IntegrityError:
            return jsonify({"error": "Duplicate source_url"}), 409
        return jsonify(job.to_dict()), 201

@job_bp.put("/jobs/<int:job_id>")
@job_bp.patch("/jobs/<int:job_id>")
def update_job(job_id: int):
    payload = request.get_json(silent=True) or {}
    errors = _validate_job_payload(payload, is_update=True)
    if errors:
        return jsonify({"error": errors}), 400
    with session_scope() as s:
        job = s.get(Job, job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        for field in ["title", "company", "location", "job_type", "salary_text", "source_url", "description"]:
            if field in payload and payload[field] is not None:
                value = payload[field].strip() if isinstance(payload[field], str) else payload[field]
                setattr(job, field, value)
        if "posting_date" in payload:
            pd = payload["posting_date"]
            job.posting_date = dateparser.isoparse(pd).date() if pd else None
        if "posted_at" in payload:
            job.posted_at = _parse_posted_at(payload.get("posted_at"))
        if "tags" in payload:
            tags = payload.get("tags") or []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            job.tags = _ensure_tags(s, tags)
        try:
            s.flush()
        except IntegrityError:
            return jsonify({"error": "Duplicate source_url"}), 409
        return jsonify(job.to_dict())

@job_bp.delete("/jobs/<int:job_id>")
def delete_job(job_id: int):
    with session_scope() as s:
        job = s.get(Job, job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        s.delete(job)
        return "", 204

@job_bp.post("/jobs/bulk")
def bulk_insert_jobs():
    body = request.get_json(silent=True) or {}
    items = body.get("items") or []
    dry_run = bool(body.get("dry_run", False))
    if not isinstance(items, list) or not items:
        return jsonify({"error": "items must be a non-empty array"}), 400

    results = []
    inserted = skipped = invalid = failed = 0

    with session_scope() as s:
        for idx, payload in enumerate(items):
            v = _validate_job_payload(payload, is_update=False)
            if v:
                invalid += 1
                results.append({"index": idx, "status": "invalid", "reason": v})
                continue

            pd = None
            if payload.get("posting_date"):
                try:
                    pd = dateparser.isoparse(payload["posting_date"]).date()
                except Exception:
                    pass
            pa = _parse_posted_at(payload.get("posted_at"))

            candidate = None
            if payload.get("source_url"):
                candidate = s.execute(select(Job).where(Job.source_url == payload["source_url"])).unique().scalar_one_or_none()
            if not candidate:
                candidate = s.execute(select(Job).where(
                    func.lower(Job.title) == payload["title"].strip().lower(),
                    func.lower(Job.company) == payload["company"].strip().lower(),
                    func.lower(Job.location) == payload["location"].strip().lower(),
                    Job.posting_date == pd,
                )).unique().scalar_one_or_none()

            if candidate:
                skipped += 1
                results.append({"index": idx, "status": "skipped-duplicate", "existing_id": candidate.id, "existing_source_url": candidate.source_url})
                continue

            if dry_run:
                inserted += 1
                results.append({"index": idx, "status": "would-insert"})
                continue

            job = Job(
                title=payload["title"].strip(),
                company=payload["company"].strip(),
                location=payload["location"].strip(),
                description=payload.get("description") or None,
                posting_date=pd,
                posted_at=pa,
                job_type=payload.get("job_type"),
                salary_text=payload.get("salary_text"),
                source_url=(payload.get("source_url") or None),
            )
            tags = payload.get("tags") or []
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            job.tags = _ensure_tags(s, tags)

            s.add(job)
            try:
                s.flush()
                inserted += 1
                results.append({"index": idx, "status": "inserted", "id": job.id})
            except IntegrityError as e:
                s.rollback()
                failed += 1
                results.append({"index": idx, "status": "error", "reason": "constraint", "detail": str(e.orig)})

    summary = {"inserted": inserted, "skipped": skipped, "invalid": invalid, "failed": failed}
    return jsonify({"summary": summary, "results": results})
