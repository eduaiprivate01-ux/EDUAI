"""SQL persistence for EduAI's curriculum, indexed material, and chat records."""

import json
import uuid

from database import connect
from api_schemas import (
    AdminEvent,
    AdminMetrics,
    CatalogRecord,
    ChatMessage,
    ChatSession,
    DocumentRecord,
    PracticeSession,
    StoredDocumentRecord,
    json_dict,
    json_dicts,
)


CATALOG_TYPES = ("Course", "Semester", "Subject")


def catalog_values(item_type, **parents):
    if item_type not in CATALOG_TYPES:
        raise ValueError("Unknown curriculum item type.")
    clauses = ["item_type = %s"]
    values = [item_type]
    for key in ("course", "semester", "subject"):
        value = parents.get(key)
        if value is not None:
            clauses.append(f"{key} = %s")
            values.append(value)
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT DISTINCT name FROM eduai_catalog WHERE {' AND '.join(clauses)} ORDER BY name",
                tuple(values),
            )
            return [row[0] for row in cursor.fetchall()]
    finally:
        connection.close()


def catalog_records():
    connection = connect()
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT catalog_id, item_type, name, course, semester, subject, created_by, created_at "
                "FROM eduai_catalog ORDER BY course, semester, subject, item_type, name"
            )
            return json_dicts(CatalogRecord, cursor.fetchall())
    finally:
        connection.close()


def add_catalog_path(course, semester, subject, created_by):
    values = [str(value).strip() for value in (course, semester, subject)]
    if not all(values):
        raise ValueError("Fill in Course, Semester, and Subject.")
    course, semester, subject = values
    rows = [
        ("Course", course, "", "", "", created_by),
        ("Semester", semester, course, "", "", created_by),
        ("Subject", subject, course, semester, "", created_by),
    ]
    connection = connect()
    try:
        with connection.cursor() as cursor:
            added = 0
            for row in rows:
                cursor.execute(
                    "SELECT catalog_id FROM eduai_catalog WHERE item_type = %s AND name = %s "
                    "AND course = %s AND semester = %s AND subject = %s LIMIT 1",
                    row[:5],
                )
                if cursor.fetchone() is None:
                    cursor.execute(
                        "INSERT INTO eduai_catalog "
                        "(item_type, name, course, semester, subject, created_by) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        row,
                    )
                    added += 1
        connection.commit()
        return added
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def insert_document_record(record):
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO eduai_documents "
                "(document_id, owner_eduai_id, visibility, course, semester, subject, "
                "document_type, title, original_filename, storage_path, mime_type, status) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'indexing')",
                (
                    record["document_id"], record["owner_eduai_id"], record["visibility"],
                    record["course"], record["semester"], record["subject"],
                    record["document_type"], record["title"], record["original_filename"],
                    record["storage_path"], record["mime_type"],
                ),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def complete_document_record(document_id, chunk_count):
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE eduai_documents SET status = 'ready', chunk_count = %s WHERE document_id = %s",
                (int(chunk_count), document_id),
            )
        connection.commit()
    finally:
        connection.close()


def remove_document_record(document_id):
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM eduai_documents WHERE document_id = %s", (document_id,))
        connection.commit()
    finally:
        connection.close()


def document_record(document_id):
    connection = connect()
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM eduai_documents WHERE document_id = %s", (document_id,))
            record = cursor.fetchone()
            return json_dict(StoredDocumentRecord, record) if record else None
    finally:
        connection.close()


def user_can_access_document(record, owner_eduai_id, role):
    if not record:
        return False
    if role == "Admin":
        return True
    if record["visibility"] == "shared":
        return True
    return record["owner_eduai_id"] == str(owner_eduai_id)


def list_documents(owner_eduai_id, role, **filters):
    clauses = ["status = 'ready'"]
    values = []
    # The tutor sees shared records and the current user's private records,
    # including when the caller is an administrator.
    clauses.append("(visibility = 'shared' OR owner_eduai_id = %s)")
    values.append(str(owner_eduai_id))
    for key in ("course", "semester", "subject", "document_type"):
        value = filters.get(key)
        if value:
            clauses.append(f"{key} = %s")
            values.append(value)
    connection = connect()
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT document_id, owner_eduai_id, visibility, course, semester, subject, "
                "document_type, title, original_filename, status, chunk_count, created_at "
                f"FROM eduai_documents WHERE {' AND '.join(clauses)} "
                "ORDER BY created_at DESC",
                tuple(values),
            )
            return json_dicts(DocumentRecord, cursor.fetchall())
    finally:
        connection.close()


def accessible_document_ids(owner_eduai_id, document_ids, role, **filters):
    """Validate a bounded set of vector candidates against SQL access rules.

    Vector search supplies the candidate IDs, so this avoids loading every
    visible document row into Python for each RAG query. RAG access is limited
    to shared documents and private documents owned by the current user.
    """
    ids = list(dict.fromkeys(str(value) for value in document_ids if value))
    if not ids:
        return set()

    placeholders = ", ".join(["%s"] * len(ids))
    clauses = [f"document_id IN ({placeholders})", "status = 'ready'"]
    values = list(ids)
    if role != "Admin":
        clauses.append("(visibility = 'shared' OR owner_eduai_id = %s)")
        values.append(str(owner_eduai_id))
    for key in ("course", "semester", "subject"):
        value = filters.get(key)
        if value:
            clauses.append(f"{key} = %s")
            values.append(str(value))

    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT document_id FROM eduai_documents WHERE " + " AND ".join(clauses),
                tuple(values),
            )
            return {row[0] for row in cursor.fetchall()}
    finally:
        connection.close()


def save_chat_message(session_id, owner_eduai_id, role, content, citations=None, context=None):
    if role not in {"user", "assistant"}:
        raise ValueError("Chat role must be user or assistant.")
    context = context or {}
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO eduai_chat_messages "
                "(session_id, owner_eduai_id, role, content, citations, course, semester, subject) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    session_id, str(owner_eduai_id), role, content,
                    json.dumps(citations or [], ensure_ascii=False), context.get("course", ""),
                    context.get("semester", ""), context.get("subject", ""),
                ),
            )
            message_id = int(cursor.lastrowid)
        connection.commit()
        return message_id
    finally:
        connection.close()


def list_chat_sessions(owner_eduai_id):
    connection = connect()
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT session_id, MIN(created_at) AS started_at, MAX(created_at) AS updated_at, "
                "COUNT(*) AS message_count "
                "FROM eduai_chat_messages WHERE owner_eduai_id = %s "
                "GROUP BY session_id ORDER BY updated_at DESC",
                (str(owner_eduai_id),),
            )
            sessions = cursor.fetchall()
            for session in sessions:
                cursor.execute(
                    "SELECT content FROM eduai_chat_messages "
                    "WHERE owner_eduai_id = %s AND session_id = %s AND role = 'user' "
                    "ORDER BY message_id LIMIT 1",
                    (str(owner_eduai_id), session["session_id"]),
                )
                first_message = cursor.fetchone()
                session["title"] = first_message["content"] if first_message else "Study conversation"
            return json_dicts(ChatSession, sessions)
    finally:
        connection.close()


def get_chat_messages(session_id, owner_eduai_id):
    connection = connect()
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT m.message_id, m.role, m.content, m.citations, m.course, m.semester, "
                "m.subject, m.created_at, f.rating AS feedback "
                "FROM eduai_chat_messages m LEFT JOIN eduai_chat_feedback f "
                "ON f.message_id = m.message_id AND f.owner_eduai_id = m.owner_eduai_id "
                "WHERE m.session_id = %s AND m.owner_eduai_id = %s "
                "ORDER BY m.message_id",
                (session_id, str(owner_eduai_id)),
            )
            rows = cursor.fetchall()
            for row in rows:
                try:
                    parsed_citations = json.loads(row["citations"] or "[]")
                    row["citations"] = parsed_citations if isinstance(parsed_citations, list) else []
                except (TypeError, ValueError):
                    row["citations"] = []
            return json_dicts(ChatMessage, rows)
    finally:
        connection.close()


def save_practice_session(owner_eduai_id, context, question_type, question_count, content, citations):
    practice_id = str(uuid.uuid4())
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO eduai_practice_sessions "
                "(practice_id, owner_eduai_id, course, semester, subject, question_type, "
                "question_count, content, citations) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    practice_id, str(owner_eduai_id), context.get("course", ""),
                    context.get("semester", ""), context.get("subject", ""),
                    question_type, int(question_count), content,
                    json.dumps(citations or [], ensure_ascii=False),
                ),
            )
        connection.commit()
        return practice_id
    finally:
        connection.close()


def save_chat_feedback(message_id, owner_eduai_id, rating):
    """Save a student's helpful/not-helpful rating for their assistant reply."""
    if rating not in {"helpful", "not_helpful"}:
        raise ValueError("Feedback must be helpful or not helpful.")
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM eduai_chat_messages WHERE message_id = %s "
                "AND owner_eduai_id = %s AND role = 'assistant'",
                (int(message_id), str(owner_eduai_id)),
            )
            if cursor.fetchone() is None:
                raise PermissionError("This reply is not available for feedback.")
            cursor.execute(
                "INSERT INTO eduai_chat_feedback (message_id, owner_eduai_id, rating) "
                "VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE rating = VALUES(rating)",
                (int(message_id), str(owner_eduai_id), rating),
            )
        connection.commit()
    finally:
        connection.close()


def get_feedback_metrics():
    connection = connect()
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS total, "
                "SUM(rating = 'helpful') AS helpful, "
                "SUM(rating = 'not_helpful') AS not_helpful "
                "FROM eduai_chat_feedback"
            )
            row = cursor.fetchone()
            return {
                "total": int(row["total"] or 0),
                "helpful": int(row["helpful"] or 0),
                "not_helpful": int(row["not_helpful"] or 0),
            }
    finally:
        connection.close()


def save_practice_attempt(owner_eduai_id, practice_id, context, correct_count, total_questions):
    """Record a self-scored attempt and schedule a spaced review interval."""
    total_questions = int(total_questions)
    correct_count = int(correct_count)
    if total_questions < 1 or not 0 <= correct_count <= total_questions:
        raise ValueError("Correct answers must be between zero and the question count.")
    course = str(context.get("course", ""))
    semester = str(context.get("semester", ""))
    subject = str(context.get("subject", ""))
    owner = str(owner_eduai_id)
    accuracy = correct_count / total_questions
    connection = connect()
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT interval_days FROM eduai_practice_attempts "
                "WHERE owner_eduai_id = %s AND course = %s AND semester = %s AND subject = %s "
                "ORDER BY created_at DESC LIMIT 1",
                (owner, course, semester, subject),
            )
            previous = cursor.fetchone()
            previous_interval = int(previous["interval_days"]) if previous else 1
            if accuracy < 0.5:
                interval_days = 1
            elif accuracy < 0.8:
                interval_days = min(7, max(2, round(previous_interval * 1.5)))
            else:
                interval_days = min(30, max(7, previous_interval * 2))
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO eduai_practice_attempts "
                "(attempt_id, practice_id, owner_eduai_id, course, semester, subject, "
                "correct_count, total_questions, accuracy, interval_days, next_review_at) "
                "SELECT %s, p.practice_id, %s, %s, %s, %s, %s, %s, %s, %s, "
                "DATE_ADD(NOW(), INTERVAL %s DAY) FROM eduai_practice_sessions p "
                "WHERE p.practice_id = %s AND p.owner_eduai_id = %s",
                (
                    str(uuid.uuid4()), owner, course, semester, subject, correct_count,
                    total_questions, accuracy, interval_days, interval_days,
                    str(practice_id), owner,
                ),
            )
            if cursor.rowcount != 1:
                raise PermissionError("This practice set does not belong to your account.")
        connection.commit()
        return {"accuracy": accuracy, "interval_days": interval_days}
    finally:
        connection.close()


def list_practice_attempts(owner_eduai_id, limit=50):
    connection = connect()
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT course, semester, subject, correct_count, total_questions, accuracy, "
                "interval_days, next_review_at, created_at "
                "FROM eduai_practice_attempts WHERE owner_eduai_id = %s "
                "ORDER BY created_at DESC LIMIT %s",
                (str(owner_eduai_id), int(limit)),
            )
            return cursor.fetchall()
    finally:
        connection.close()


def adaptive_review_subjects(owner_eduai_id):
    """Return each subject's latest self-scored review and whether it is due."""
    connection = connect()
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT course, semester, subject, accuracy, interval_days, next_review_at, created_at, "
                "(next_review_at <= NOW()) AS due "
                "FROM eduai_practice_attempts WHERE owner_eduai_id = %s "
                "ORDER BY created_at DESC",
                (str(owner_eduai_id),),
            )
            rows = cursor.fetchall()
            seen = set()
            latest = []
            for row in rows:
                key = (row["course"], row["semester"], row["subject"])
                if key in seen:
                    continue
                seen.add(key)
                row["due"] = bool(row["due"])
                latest.append(row)
            return latest
    finally:
        connection.close()


def list_practice_sessions(owner_eduai_id):
    connection = connect()
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT practice_id, course, semester, subject, question_type, question_count, "
                "created_at FROM eduai_practice_sessions WHERE owner_eduai_id = %s "
                "ORDER BY created_at DESC LIMIT 30",
                (str(owner_eduai_id),),
            )
            return json_dicts(PracticeSession, cursor.fetchall())
    finally:
        connection.close()


def get_admin_metrics():
    connection = connect()
    try:
        with connection.cursor(dictionary=True) as cursor:
            result = {}
            cursor.execute("SELECT COUNT(*) AS total FROM users WHERE status = 'active'")
            result["active_users"] = cursor.fetchone()["total"]
            cursor.execute("SELECT COUNT(*) AS total FROM eduai_catalog WHERE item_type = 'Course'")
            result["courses"] = cursor.fetchone()["total"]
            cursor.execute("SELECT COUNT(*) AS total FROM eduai_documents WHERE status = 'ready'")
            result["materials"] = cursor.fetchone()["total"]
            cursor.execute("SELECT COUNT(*) AS total FROM eduai_chat_messages WHERE role = 'user'")
            result["questions"] = cursor.fetchone()["total"]
            return json_dict(AdminMetrics, result)
    finally:
        connection.close()


def record_admin_event(admin_eduai_id, action, target):
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO eduai_admin_events (admin_eduai_id, action, target) VALUES (%s, %s, %s)",
                (str(admin_eduai_id), action, target),
            )
        connection.commit()
    finally:
        connection.close()


def list_admin_events(limit=100):
    connection = connect()
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT admin_eduai_id, action, target, created_at FROM eduai_admin_events "
                "ORDER BY event_id DESC LIMIT %s",
                (int(limit),),
            )
            return json_dicts(AdminEvent, cursor.fetchall())
    finally:
        connection.close()
