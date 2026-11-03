import sqlite3
from pathlib import Path

from app.schemas import TaskCreateRequest

TASK_COLUMNS = "id,title,description,status,owner,priority,created_at"


def connect_database(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    initialize_database(connection)
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.execute(
        "CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT NOT NULL, status TEXT NOT NULL, owner TEXT NOT NULL, priority TEXT NOT NULL, created_at TEXT NOT NULL)"
    )
    count = connection.execute("SELECT COUNT(*) AS total FROM tasks").fetchone()["total"]
    if count == 0:
        connection.execute(
            "INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES ('Refactor login','Separar responsabilidades en frontend','TODO','student','HIGH',datetime('now'))"
        )
        connection.execute(
            "INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES ('Review API','Revisar seguridad de endpoints','IN_PROGRESS','student','MEDIUM',datetime('now'))"
        )
        connection.execute(
            "INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES ('Trainer notes','Preparar retrospectiva','TODO','trainer','LOW',datetime('now'))"
        )
        connection.commit()


class TaskRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_by_owner(self, owner: str) -> list[sqlite3.Row]:
        sql = f"SELECT {TASK_COLUMNS} FROM tasks WHERE owner=? ORDER BY id"
        return self._connection.execute(sql, (owner,)).fetchall()

    def create(self, task: TaskCreateRequest, owner: str) -> sqlite3.Row:
        sql = "INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES (?,?,?,?,?,datetime('now'))"
        cursor = self._connection.execute(
            sql,
            (
                task.title,
                task.description,
                task.status.value,
                owner,
                task.priority.value,
            ),
        )
        self._connection.commit()
        return self._connection.execute(
            f"SELECT {TASK_COLUMNS} FROM tasks WHERE id=?",
            (cursor.lastrowid,),
        ).fetchone()

    def summary_rows(self, owner: str) -> list[sqlite3.Row]:
        return self._connection.execute(
            "SELECT status,priority FROM tasks WHERE owner=?", (owner,)
        ).fetchall()