# Pruebas de API

## Alcance

Componente cubierto: `api`. La matriz sigue las cinco rutas y los estados de éxito/error descritos en [ENDPOINTS.md](ENDPOINTS.md). Los casos de autorización y token caracterizan el comportamiento actual; no certifican que la identidad del token sea confiable. Los ejemplos de `500` son fallos internos inyectados en pruebas y solo se exige el estado, porque la API no define un cuerpo estable para ellos.

## Matriz de casos

| endpoint | caso | tipo | resultado esperado |
|---|---|---|---|
| `GET /api/tasks` | Listado de tareas semilla | Camino feliz | `200`; lista de dos tareas de `student`, con campos del contrato. |
| `GET /api/tasks` | `owner` vacío | Borde | `200`; se usa el usuario autenticado y no se cambia el propietario. |
| `GET /api/tasks` | Sin `Authorization` | Error | `401`; `{"detail":"Invalid token"}`. |
| `GET /api/tasks` | Solicitar otro `owner` | Error | `403`; `{"detail":"Not authorized to access this owner"}`. |
| `GET /api/tasks` | Error de SQLite inyectado | Error interno | `500`; cuerpo no contractual, no se aserta. |
| `POST /api/tasks` | Crear con campos válidos | Camino feliz | `201`; objeto de tarea y defaults comprobados. |
| `POST /api/tasks` | Valores permitidos de `status` y `priority` | Camino feliz | `201`; valores exactos del catálogo aparecen en la respuesta. |
| `POST /api/tasks` | `status` o `priority` desconocidos, con casing/espacios distintos o vacíos | Error de validación | `422`; campo identificado en el error y ninguna tarea creada. |
| `POST /api/tasks` | JSON vacío | Borde | `201`; defaults `title=""`, `description=""`, `status="TODO"`, `priority="MEDIUM"` y owner autenticado. |
| `POST /api/tasks` | Sin `Authorization` | Error | `401`; `{"detail":"Invalid token"}`. |
| `POST /api/tasks` | Override de `owner` | Error | `403`; `{"detail":"Not authorized to access this owner"}`. |
| `POST /api/tasks` | Body JSON que no es objeto | Error | `422`; detalle Pydantic observado para `[]`. |
| `POST /api/tasks` | Error SQLite al crear | Error interno | `500`; cuerpo no contractual, no se aserta. |
| `GET /api/summary` | Resumen con tareas | Camino feliz | `200`; `total`, `byStatus` y `highPriorityOpen` comprobados. |
| `GET /api/summary` | Estados `DONE` y `ARCHIVED` de prioridad `HIGH` | Regla de dominio | `200`; no se cuentan en `highPriorityOpen`. |
| `GET /api/tasks` y `GET /api/summary` | Valores legacy fuera del catálogo | Compatibilidad | `200`; el listado los conserva y el resumen los agrupa por el estado almacenado. |
| `GET /api/summary` | Usuario sin tareas | Borde | `200`; `total=0`, `byStatus={}`, `highPriorityOpen=0`. |
| `GET /api/summary` | Sin `Authorization` | Error | `401`; `{"detail":"Invalid token"}`. |
| `GET /api/summary` | Solicitar otro `owner` | Error | `403`; `{"detail":"Not authorized to access this owner"}`. |
| `GET /api/summary` | Error SQLite inyectado | Error interno | `500`; cuerpo no contractual, no se aserta. |
| `POST /api/requirements` | Cargar `requirements.txt` | Camino feliz | `201`; owner, nombre, ruta y tamaño `24` comprobados; archivo presente. |
| `POST /api/requirements` | Archivo vacío sin extensión | Borde | `201`; `size=0`, nombre sin extensión y archivo vacío almacenado. Es comportamiento observado, no una aprobación de la política de carga. |
| `POST /api/requirements` | Sin `Authorization` | Error | `401`; `{"detail":"Invalid token"}`. |
| `POST /api/requirements` | Falta la parte `file` | Error | `422`; detalle Pydantic observado para el campo requerido. |
| `POST /api/requirements` | Error de escritura inyectado | Error interno | `500`; cuerpo no contractual, no se aserta. |
| `GET /api/backend-health` | Backend upstream responde `503` | Camino feliz del endpoint | `200` de la API; `status=503` y body upstream preservado como texto. |
| `GET /api/backend-health` | Body upstream vacío | Borde | `200`; `status=200`, `body=""`. |
| `GET /api/backend-health` | Error upstream capturado (`HTTPError`) | Error upstream controlado | `200`; `status=0`, mensaje genérico. |
| `GET /api/backend-health` | Sin `Authorization` | Error | `401`; `{"detail":"Invalid token"}`. |
| `GET /api/backend-health` | Excepción no capturada inyectada | Error interno | `500`; cuerpo no contractual, no se aserta. |

Además, se conservan las pruebas de SQL con comillas (`H-API-03`), las pruebas del contrato a través de rutas y capas (`H-API-06`), las pruebas de validación/modelos y errores genéricos (`H-API-07`) y las pruebas del catálogo aprobado y lectura de valores legacy (`H-API-09`). El rechazo de `owner` se prueba como comportamiento actual; no se cuenta como cierre de una autorización basada en identidad firmada.

## Código de los tests

El código ejecutable completo, incluidos los tests preexistentes y sus aserciones reforzadas, está en [api/tests/test_api.py](../api/tests/test_api.py). A continuación se muestran las funciones nuevas para bordes y errores; usan los helpers `create_app` y `headers` definidos en ese archivo.

```python
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    ("method", "path", "request_kwargs"),
    [
        pytest.param("get", "/api/tasks", {}, id="list-tasks"),
        pytest.param("post", "/api/tasks", {"json": {}}, id="create-task"),
        pytest.param("get", "/api/summary", {}, id="summary"),
        pytest.param(
            "post",
            "/api/requirements",
            {"files": {"file": ("requirements.txt", b"content", "text/plain")}},
            id="upload-requirement",
        ),
        pytest.param("get", "/api/backend-health", {}, id="backend-health"),
    ],
)
def test_all_endpoints_reject_missing_authentication(
    method: str, path: str, request_kwargs: dict, tmp_path: Path
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = getattr(client, method)(path, **request_kwargs)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


def test_list_tasks_with_empty_owner_uses_authenticated_identity(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks?owner=", headers=headers())

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert all(task["owner"] == "student" for task in response.json())


def test_create_task_with_empty_payload_uses_all_defaults(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/tasks", headers=headers(), json={})

    payload = response.json()
    assert response.status_code == 201
    assert payload["id"] == 4
    assert payload["title"] == ""
    assert payload["description"] == ""
    assert payload["status"] == "TODO"
    assert payload["owner"] == "student"
    assert payload["priority"] == "MEDIUM"
    assert isinstance(payload["createdAt"], str)
    assert payload["createdAt"]


def test_summary_returns_counts_for_empty_owner_dataset(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        app.state.connection.execute("DELETE FROM tasks WHERE owner=?", ("student",))
        app.state.connection.commit()
        response = client.get("/api/summary", headers=headers())

    assert response.status_code == 200
    assert response.json() == {
        "owner": "student",
        "total": 0,
        "byStatus": {},
        "highPriorityOpen": 0,
    }


def test_summary_rejects_other_owner(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/summary?owner=trainer", headers=headers())

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authorized to access this owner"}


def test_uploads_empty_file_without_extension(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements", b"", "application/octet-stream")},
        )

    assert response.status_code == 201
    assert response.json() == {
        "owner": "student",
        "fileName": "requirements",
        "storedAt": str(upload_dir / "requirements"),
        "size": 0,
    }
    assert (upload_dir / "requirements").read_bytes() == b""


def test_upload_requirement_without_file_returns_422(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/requirements", headers=headers())

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "missing",
                "loc": ["body", "file"],
                "msg": "Field required",
                "input": None,
            }
        ]
    }


def test_backend_health_preserves_empty_upstream_body(monkeypatch, tmp_path: Path) -> None:
    class EmptyResponse:
        status = 200
        data = b""

    class StubPoolManager:
        def request(self, method: str, url: str, timeout: float) -> EmptyResponse:
            return EmptyResponse()

    monkeypatch.setattr("app.services.urllib3.PoolManager", StubPoolManager)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())

    assert response.status_code == 200
    assert response.json() == {"requestedBy": "student", "status": 200, "body": ""}


@pytest.mark.parametrize(
    ("method", "path", "failure_target", "request_kwargs"),
    [
        pytest.param("get", "/api/tasks", "app.repositories.TaskRepository.list_by_owner", {}, id="list-db"),
        pytest.param("post", "/api/tasks", "app.repositories.TaskRepository.create", {"json": {}}, id="create-db"),
        pytest.param("get", "/api/summary", "app.repositories.TaskRepository.summary_rows", {}, id="summary-db"),
        pytest.param("post", "/api/requirements", "app.services.Path.write_bytes", {"files": {"file": ("requirements.txt", b"content", "text/plain")}}, id="upload-write"),
        pytest.param("get", "/api/backend-health", "app.services.urllib3.PoolManager", {}, id="backend-unexpected"),
    ],
)
def test_unhandled_internal_failures_return_500(
    monkeypatch,
    method: str,
    path: str,
    failure_target: str,
    request_kwargs: dict,
    tmp_path: Path,
) -> None:
    def fail(*args, **kwargs):
        raise sqlite3.OperationalError("injected internal failure")

    monkeypatch.setattr(failure_target, fail)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = getattr(client, method)(path, headers=headers(), **request_kwargs)

    assert response.status_code == 500
```

## Ejecuciones

Las ejecuciones de prueba se hicieron con cwd `api/`. Las ejecuciones válidas usaron `api/.venv/Scripts/python.exe`; el primer intento con Python del sistema se registra aparte porque no llegó a pytest.

| comando | componente e IDs resueltos considerados | código de salida | resultado |
|---|---|---:|---|
| `python -m pytest -q tests/test_api.py -k all_endpoints_reject_missing_auth` usando Python del sistema | `api`; H-API-06, H-API-07 | `1` | No ejecutó pytest: el intérprete del sistema no tenía instalado el módulo. No cuenta como resultado de pruebas. |
| `.\.venv\Scripts\python.exe -m pytest -q tests/test_api.py -k all_endpoints_reject_missing_auth` | `api`; H-API-06, H-API-07 | `0` | `5 passed`, 2 warnings deprecación. |
| `.\.venv\Scripts\python.exe -m pytest -q tests/test_api.py` | `api`; H-API-03, H-API-06, H-API-07 | `1` | `29 passed`, 1 failed por expectativa documental incorrecta del error Pydantic (`model_type`). Se corrigieron test y ejemplo de `ENDPOINTS.md` al valor observado (`model_attributes_type`). |
| `.\.venv\Scripts\python.exe -m pytest -q tests/test_api.py` | `api`; H-API-03, H-API-06, H-API-07 | `0` | `30 passed`, 2 warnings deprecación. |
| `.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing` | `api`; H-API-03, H-API-06, H-API-07 | `0` | `30 passed`; cobertura global `100%`, 188/188 sentencias y 10/10 ramas. |

Los dos warnings deprecados pertenecen al uso de `httpx` por `starlette.testclient` y al alias `anyio.abc.BlockingPortal`; no causaron fallos.

## Cobertura

- **Método:** `pytest-cov`/Coverage.py con `--cov=app --cov-report=term-missing`; `branch = true` está configurado en `api/pyproject.toml`.
- **Cobertura global de aplicación:** 188 sentencias cubiertas de 188 (188/188), 10 ramas cubiertas de 10 (10/10), cobertura reportada `100%`.
- **Código de aplicación modificado en este paso:** ninguno; numerador y denominador de cobertura modificada son N/A. Solo se modificó `api/tests/test_api.py`, que no es el target de `--cov=app`. La cobertura global supera el umbral del 85%, pero no se presenta como cobertura de código de producción modificado.
- **Artefacto del reporte:** salida de terminal `term-missing` registrada arriba; no se generó un reporte HTML/XML.

## Fallos

- La primera orden usó Python del sistema y terminó antes de pytest porque no encontraba `pytest`; se repitió correctamente con el intérprete del entorno virtual.
- La primera suite detectó que el ejemplo `422` de `POST /api/tasks` no coincidía con Pydantic instalado. Se actualizaron la aserción y [ENDPOINTS.md](ENDPOINTS.md); la repetición terminó con `30 passed`.
- No quedan fallos de pruebas en la última ejecución registrada.

## Pendientes

- La prueba de `owner` verifica que la implementación rechaza un username discrepante, pero no prueba una identidad autenticada criptográficamente. El token legacy sigue siendo falsificable; no se declara resuelta la autorización basada en identidad.
- `POST /api/requirements` acepta actualmente un archivo vacío sin extensión. El test caracteriza el comportamiento observado; no define una política segura ni límites de tamaño/extensión.
- Los `500` se verifican por código de estado solamente porque el cuerpo depende del middleware/deploy y no está fijado como contrato.
- No se caracterizó un multipart malformado distinto de omitir `file`; la respuesta está anotada como pregunta abierta en `ENDPOINTS.md`.
- El análisis SCA de dependencias no se volvió a ejecutar en este paso; la evidencia previa permanece en `PLAN.md`.

## Pruebas propuestas

- Acordar el contrato JWT con el emisor y añadir casos para firma inválida, expiración e issuer/audience antes de considerar confiable la identidad.
- Acordar extensión y tamaño máximo para cargas; después añadir pruebas de nombre/ruta, tipo no permitido y exceso de tamaño, sin cambiar las expectativas antes de la decisión.
- Caracterizar el parser con multipart malformado y documentar el estado/cuerpo real de la versión desplegada.
- Si se requiere un cuerpo estable para errores `500`, definirlo en la aplicación y entonces probarlo como contrato.

## Documentos consultados

- [README.md](../README.md)
- [RETO.md](../RETO.md)
- [docs/GOOD_PRACTICES.md](GOOD_PRACTICES.md)
- [HALLAZGOS.md](../HALLAZGOS.md)
- [PLAN.md](../PLAN.md)
- [docs/ENDPOINTS.md](ENDPOINTS.md)
- Código API: `api/app/` y `api/tests/test_api.py`.