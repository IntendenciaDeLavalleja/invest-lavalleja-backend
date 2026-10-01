# Backend de Gianna

API Python autónoma: FastAPI, Uvicorn, LangGraph, Ollama Cloud, embeddings, reranker, LanceDB/NumPy y administración con 2FA. No sirve el frontend ni necesita Nginx.

[Arquitectura y flujos del sistema](https://github.com/NebyX1/invest-lavalleja-rag-chat/blob/main/Arquitectura.md): API, agente, recuperación, cupos, administración e indexación.

Este repositorio contiene exclusivamente el backend, situado en la raíz para construirlo directamente con Docker o Coolify. El [frontend de Invest Lavalleja](https://github.com/IntendenciaDeLavalleja/invest-lavalleja-frontend) se despliega como otro servicio.

## Estructura

- `main.py`, `chat_access.py` y `config.py`: API, acceso, cupos y configuración.
- `graph.py`, `advisor.py`, `tools.py` y `prompt.py`: agente y herramientas.
- `rag.py`, `store.py` y `lexical.py`: recuperación e índice vectorial.
- `admin_*.py` y `knowledge_*.py`: administración, 2FA, documentos y versiones.
- `ingest.py` y `rag-data/`: extracción Word y ubicación local de documentos fuente.
- `scripts/` y `tests/`: diagnóstico y validación.
- `Dockerfile`, `docker/` y `compose.yaml`: contenedor Python independiente.

## Inicio con Docker

Copiar `.env.example` a `.env` y configurar las variables antes de ejecutar:

```sh
docker compose up --build -d
```

O construir sólo esta carpeta:

```sh
docker build -t invest-backend .
```

## Despliegue en Coolify

Seleccionar Dockerfile, directorio base `/`, Dockerfile `/Dockerfile`, puerto interno **8010** y healthcheck **/api/health**. Montar un volumen persistente **/data** con UID/GID **10001**. Usar un worker y una réplica para la activación del conocimiento existente.

Configurar `CORS_ORIGINS` y `ADMIN_ALLOWED_ORIGINS` con el origen HTTPS del frontend, sin barra final, y `PROXY_TRUSTED_IPS` con la red exacta del proxy. El frontend conecta mediante `BACKEND_URL` para el proxy Nginx o `VITE_API_URL` para CORS directo.

Definir `OLLAMA_API_KEY`, `OLLAMA_MODEL`, una `ADMIN_SECRET_KEY` estable de al menos 32 caracteres y las variables SMTP exclusivamente en el backend. `ADMIN_EMAIL` y `ADMIN_PASSWORD` permiten crear la primera cuenta; retirar la contraseña del entorno después del primer arranque.

Una instalación nueva arranca sin conocimiento: el administrador debe cargar el Word o un JSONL validado desde el panel del frontend. Hasta entonces, la salud informa `knowledge_ready=false` y el chat devuelve 503. El índice existente se adopta si se monta en `/data/legacy-index`; los modelos se guardan en `/data/models`.

## Persistencia

No persiste conversaciones. `chat-quota.sqlite3` conserva exclusivamente contadores por IP/sesión con hashes HMAC: 20 consultas aceptadas y 600 segundos de espera al agotarlas. SQLite también conserva la administración, sus sesiones y las versiones de documentos.

## Diagnóstico y pruebas

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q tests
python scripts/check_smtp.py
```

La comprobación SMTP valida TLS y autenticación sin enviar correo. Para uso local sin Docker, dejar las rutas de datos por defecto y usar `ADMIN_COOKIE_SECURE=false` sólo en HTTP local.

Las pruebas de integración en `tests/deployment/` utilizan imágenes separadas de frontend y backend, proveedores de prueba y un índice local. Sus requisitos y resultados están en el [informe de validación de la integración](https://github.com/NebyX1/invest-lavalleja-rag-chat/blob/main/PRODUCTION-VALIDATION.md).

Ver la [guía de despliegue y administración](https://github.com/NebyX1/invest-lavalleja-rag-chat/blob/main/Admin-y-Coolify.md).
