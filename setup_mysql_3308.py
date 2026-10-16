"""Provision EduAI on the MySQL 26.7 Windows service configured for port 3308."""

import os
from getpass import getpass

from database import connect, ensure_schema, mysql_config


HOST = "127.0.0.1"
PORT = 3308
DATABASE = "eduai"
APP_USER = "eduai_app"


def main():
    settings = mysql_config()
    if settings["host"] != HOST or settings["database"] != DATABASE or settings["user"] != APP_USER:
        raise SystemExit(
            "Expected .streamlit/secrets.toml to configure 127.0.0.1 / eduai / eduai_app."
        )
    app_password = settings.get("password")
    if not app_password:
        raise SystemExit("The MySQL application password is missing from local settings.")

    root_password = getpass("MySQL root password: ")
    if not root_password:
        raise SystemExit("A MySQL root password is required.")

    try:
        import mysql.connector
    except ImportError as error:
        raise SystemExit("Install mysql-connector-python in the model environment first.") from error

    connection = mysql.connector.connect(
        host=HOST,
        port=PORT,
        user="root",
        password=root_password,
        connection_timeout=5,
        charset="utf8mb4",
        use_unicode=True,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            if not str(version).startswith("26.7"):
                raise RuntimeError(
                    f"Expected MySQL 26.7 on port {PORT}; connected to {version}. No schema changes made."
                )

            cursor.execute(
                "CREATE DATABASE IF NOT EXISTS eduai "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
            )
            # MySQL may identify a loopback TCP client as either localhost or
            # 127.0.0.1. Create both exact account hosts so SQLTools and the app
            # resolve to the same private credentials on local connections.
            for app_host in ("localhost", "127.0.0.1"):
                cursor.execute(
                    f"CREATE USER IF NOT EXISTS 'eduai_app'@'{app_host}' IDENTIFIED BY %s",
                    (app_password,),
                )
                cursor.execute(
                    f"ALTER USER 'eduai_app'@'{app_host}' IDENTIFIED BY %s",
                    (app_password,),
                )
                cursor.execute(
                    f"GRANT ALL PRIVILEGES ON eduai.* TO 'eduai_app'@'{app_host}'"
                )
        connection.commit()
    finally:
        connection.close()

    # Override only the endpoint so the normal app connector reads the existing
    # private username and password without printing or copying either value.
    os.environ["MYSQL_HOST"] = HOST
    os.environ["MYSQL_PORT"] = str(PORT)
    os.environ["MYSQL_USER"] = APP_USER
    os.environ["MYSQL_PASSWORD"] = app_password
    os.environ["MYSQL_DATABASE"] = DATABASE
    ensure_schema()

    app_connection = connect()
    try:
        with app_connection.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            cursor.execute("SHOW TABLES")
            table_count = len(cursor.fetchall())
    finally:
        app_connection.close()

    print(f"EduAI database is ready on MySQL {version} at {HOST}:{PORT}.")
    print(f"Created or verified {table_count} EduAI tables. Existing database rows were preserved.")


if __name__ == "__main__":
    main()
