import hashlib
import hmac
import secrets
import uuid

from database import connect, ensure_schema


PASSWORD_ITERATIONS = 310_000


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password, stored_hash):
    try:
        algorithm, iteration_text, salt_text, expected = stored_hash.split("$", 3)
        iterations = int(iteration_text)
        if algorithm != "pbkdf2_sha256" or not 100_000 <= iterations <= 2_000_000:
            return False
        salt = bytes.fromhex(salt_text)
        expected_digest = bytes.fromhex(expected)
    except (AttributeError, TypeError, ValueError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected_digest)


def create_user_account(email, display_name, password, role="student"):
    email = email.strip().lower()
    display_name = display_name.strip()
    role = role.strip().lower()
    if "@" not in email or "." not in email.rsplit("@", 1)[-1] or not display_name:
        raise ValueError("Enter a name and a valid email address.")
    if len(password) < 8:
        raise ValueError("Use a password with at least 8 characters.")
    if role not in {"student", "teacher", "admin"}:
        raise ValueError("Choose Student, Teacher, or Admin.")

    ensure_schema()
    eduai_id = f"EDU-{uuid.uuid4().hex[:8].upper()}"
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (eduai_id, email, display_name, password_hash, role) "
                "VALUES (%s, %s, %s, %s, %s)",
                (eduai_id, email, display_name, hash_password(password), role),
            )
        connection.commit()
    except Exception as error:
        if getattr(error, "errno", None) == 1062:
            raise ValueError("An account with that email already exists.") from error
        raise
    finally:
        connection.close()
    return eduai_id


def authenticate_user(email, password):
    ensure_schema()
    connection = connect()
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT id, eduai_id, email, display_name, password_hash, role, status "
                "FROM users WHERE email = %s OR eduai_id = %s LIMIT 1",
                (email.strip().lower(), email.strip().upper()),
            )
            user = cursor.fetchone()
            if not user or user["status"] != "active" or not verify_password(password, user["password_hash"]):
                return None
            cursor.execute("UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = %s", (user["id"],))
        connection.commit()
        return {
            "id": user["eduai_id"],
            "email": user["email"],
            "name": user["display_name"],
            "role": user["role"].capitalize(),
        }
    finally:
        connection.close()


def list_user_accounts():
    connection = connect()
    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT eduai_id, email, display_name, role, status, created_at "
                "FROM users ORDER BY created_at DESC, id DESC"
            )
            return cursor.fetchall()
    finally:
        connection.close()

def delete_user_account(eduai_id):
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM users WHERE eduai_id = %s AND role IN ('student', 'teacher')",
                (eduai_id,),
            )
            deleted = cursor.rowcount == 1
        connection.commit()
        return deleted
    finally:
        connection.close()