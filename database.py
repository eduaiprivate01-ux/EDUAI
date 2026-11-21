import os
from pathlib import Path

import streamlit as st


def _load_local_env():
    """Read simple KEY=value settings without adding a hard startup dependency."""
    env_path = Path(__file__).parent / ".env"
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if not key or key in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ[key] = value


_load_local_env()

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


def mysql_config():
    secret_path = Path(__file__).parent / ".streamlit" / "secrets.toml"
    try:
        with secret_path.open("rb") as secret_file:
            settings = dict(tomllib.load(secret_file).get("mysql", {}))
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        settings = {}
    try:
        settings.update(dict(st.secrets.get("mysql", {})))
    except Exception:
        pass
    return {
        "host": os.getenv("MYSQL_HOST", settings.get("host", "127.0.0.1")),
        "port": os.getenv("MYSQL_PORT", settings.get("port", 3308)),
        "user": os.getenv("MYSQL_USER", settings.get("user")),
        "password": os.getenv("MYSQL_PASSWORD", settings.get("password")),
        "database": os.getenv("MYSQL_DATABASE", settings.get("database", "eduai")),
    }


def has_mysql_settings():
    settings = mysql_config()
    return any(os.getenv(f"MYSQL_{key.upper()}") for key in ("host", "port", "user", "password", "database")) or bool(settings.get("user") or settings.get("password"))


def is_configured():
    settings = mysql_config()
    return all(settings.get(key) for key in ("host", "port", "user", "password", "database"))


def connect():
    settings = mysql_config()
    if not all(settings.get(key) for key in ("host", "port", "user", "password", "database")):
        raise RuntimeError("Configure MySQL host, port, user, password, and database first.")
    try:
        import mysql.connector
    except ImportError as error:
        raise RuntimeError("Install mysql-connector-python to use database accounts.") from error
    try:
        settings["port"] = int(settings["port"])
    except (TypeError, ValueError) as error:
        raise RuntimeError("MYSQL_PORT must be a number.") from error
    return mysql.connector.connect(
        **settings,
        connection_timeout=5,
        charset="utf8mb4",
        use_unicode=True,
    )


def ensure_schema():
    connection = connect()
    try:
        with connection.cursor() as cursor:
            statements = ["""
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    eduai_id VARCHAR(16) NOT NULL,
                    email VARCHAR(254) NOT NULL,
                    display_name VARCHAR(120) NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role ENUM('student', 'teacher', 'admin') NOT NULL DEFAULT 'student',
                    status ENUM('active', 'inactive') NOT NULL DEFAULT 'active',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_login_at TIMESTAMP NULL DEFAULT NULL,
                    PRIMARY KEY (id),
                    UNIQUE KEY uq_users_eduai_id (eduai_id),
                    UNIQUE KEY uq_users_email (email),
                    KEY ix_users_role_status (role, status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """, """
                CREATE TABLE IF NOT EXISTS eduai_catalog (
                    catalog_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    item_type ENUM('Course', 'Semester', 'Subject') NOT NULL,
                    name VARCHAR(120) NOT NULL,
                    course VARCHAR(120) NOT NULL DEFAULT '',
                    semester VARCHAR(120) NOT NULL DEFAULT '',
                    subject VARCHAR(120) NOT NULL DEFAULT '',
                    created_by VARCHAR(16) NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (catalog_id),
                    KEY ix_catalog_type_name (item_type, name),
                    KEY ix_catalog_path (course, semester, subject)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """, """
                CREATE TABLE IF NOT EXISTS eduai_documents (
                    document_id CHAR(36) NOT NULL,
                    owner_eduai_id VARCHAR(16) NOT NULL,
                    visibility ENUM('private', 'shared') NOT NULL DEFAULT 'private',
                    course VARCHAR(120) NOT NULL DEFAULT '',
                    semester VARCHAR(120) NOT NULL DEFAULT '',
                    subject VARCHAR(120) NOT NULL DEFAULT '',
                    document_type VARCHAR(32) NOT NULL DEFAULT 'Study material',
                    title VARCHAR(255) NOT NULL,
                    original_filename VARCHAR(255) NOT NULL,
                    storage_path VARCHAR(1024) NOT NULL,
                    mime_type VARCHAR(120) NOT NULL,
                    status ENUM('indexing', 'ready', 'failed') NOT NULL DEFAULT 'indexing',
                    chunk_count INT UNSIGNED NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (document_id),
                    KEY ix_documents_visibility (visibility, status),
                    KEY ix_documents_owner (owner_eduai_id, status),
                    KEY ix_documents_subject (course, semester, subject)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """, """
                CREATE TABLE IF NOT EXISTS eduai_chat_messages (
                    message_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    session_id CHAR(36) NOT NULL,
                    owner_eduai_id VARCHAR(16) NOT NULL,
                    role ENUM('user', 'assistant') NOT NULL,
                    content LONGTEXT NOT NULL,
                    citations LONGTEXT NULL,
                    course VARCHAR(120) NOT NULL DEFAULT '',
                    semester VARCHAR(120) NOT NULL DEFAULT '',
                    subject VARCHAR(120) NOT NULL DEFAULT '',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (message_id),
                    KEY ix_chat_session (owner_eduai_id, session_id, message_id),
                    KEY ix_chat_created (owner_eduai_id, created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """, """
                CREATE TABLE IF NOT EXISTS eduai_chat_feedback (
                    message_id BIGINT UNSIGNED NOT NULL,
                    owner_eduai_id VARCHAR(16) NOT NULL,
                    rating ENUM('helpful', 'not_helpful') NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (message_id),
                    KEY ix_chat_feedback_owner (owner_eduai_id, created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """, """
                CREATE TABLE IF NOT EXISTS eduai_practice_sessions (
                    practice_id CHAR(36) NOT NULL,
                    owner_eduai_id VARCHAR(16) NOT NULL,
                    course VARCHAR(120) NOT NULL DEFAULT '',
                    semester VARCHAR(120) NOT NULL DEFAULT '',
                    subject VARCHAR(120) NOT NULL DEFAULT '',
                    question_type VARCHAR(32) NOT NULL,
                    question_count TINYINT UNSIGNED NOT NULL,
                    content LONGTEXT NOT NULL,
                    citations LONGTEXT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (practice_id),
                    KEY ix_practice_owner (owner_eduai_id, created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """, """
                CREATE TABLE IF NOT EXISTS eduai_practice_attempts (
                    attempt_id CHAR(36) NOT NULL,
                    practice_id CHAR(36) NOT NULL,
                    owner_eduai_id VARCHAR(16) NOT NULL,
                    course VARCHAR(120) NOT NULL DEFAULT '',
                    semester VARCHAR(120) NOT NULL DEFAULT '',
                    subject VARCHAR(120) NOT NULL DEFAULT '',
                    correct_count TINYINT UNSIGNED NOT NULL,
                    total_questions TINYINT UNSIGNED NOT NULL,
                    accuracy DECIMAL(5,4) NOT NULL,
                    interval_days SMALLINT UNSIGNED NOT NULL,
                    next_review_at DATETIME NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (attempt_id),
                    KEY ix_practice_attempt_owner (owner_eduai_id, created_at),
                    KEY ix_practice_due (owner_eduai_id, next_review_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """, """
                CREATE TABLE IF NOT EXISTS eduai_admin_events (
                    event_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    admin_eduai_id VARCHAR(16) NOT NULL,
                    action VARCHAR(120) NOT NULL,
                    target VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (event_id),
                    KEY ix_admin_events_created (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """]
            for statement in statements:
                cursor.execute(statement)

            # Remove legacy Unit catalog rows and the old enum option without
            # affecting courses, semesters, subjects, or uploaded documents.
            cursor.execute(
                "SELECT COLUMN_TYPE FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'eduai_catalog' "
                "AND COLUMN_NAME = 'item_type'"
            )
            item_type_column = cursor.fetchone()
            if item_type_column and "'Unit'" in item_type_column[0]:
                cursor.execute("DELETE FROM eduai_catalog WHERE item_type = 'Unit'")
                cursor.execute(
                    "ALTER TABLE eduai_catalog MODIFY COLUMN item_type "
                    "ENUM('Course', 'Semester', 'Subject') NOT NULL"
                )

            # Existing installations have an index and column for Unit. Drop
            # them once, then ensure the replacement subject lookup index exists.
            cursor.execute(
                "SELECT 1 FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'eduai_documents' "
                "AND COLUMN_NAME = 'unit'"
            )
            has_legacy_unit_column = cursor.fetchone() is not None
            if has_legacy_unit_column:
                cursor.execute(
                    "SELECT 1 FROM information_schema.STATISTICS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'eduai_documents' "
                    "AND INDEX_NAME = 'ix_documents_subject'"
                )
                if cursor.fetchall():
                    cursor.execute("ALTER TABLE eduai_documents DROP INDEX ix_documents_subject")
                cursor.execute("ALTER TABLE eduai_documents DROP COLUMN unit")

            cursor.execute(
                "SELECT 1 FROM information_schema.STATISTICS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'eduai_documents' "
                "AND INDEX_NAME = 'ix_documents_subject'"
            )
            if not cursor.fetchall():
                cursor.execute(
                    "CREATE INDEX ix_documents_subject "
                    "ON eduai_documents (course, semester, subject)"
                )
        connection.commit()
    finally:
        connection.close()


