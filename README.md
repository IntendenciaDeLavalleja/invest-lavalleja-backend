# Backend de Gianna

API Python autónoma: FastAPI, Uvicorn, LangGraph, Ollama Cloud, embeddings, reranker, LanceDB/NumPy y administración con 2FA. No sirve el frontend ni necesita Nginx.

[Arquitectura y flujos del sistema](https://github.com/NebyX1/invest-lavalleja-rag-chat/blob/main/Arquitectura.md): API, agente, recuperación, cupos, administración e indexación.

Este repositorio contiene exclusivamente el backend, situado en la raíz para construirlo directamente con Docker o Coolify. El [frontend de Invest Lavalleja](https://github.com/IntendenciaDeLavalleja/invest-lavalleja-frontend) se despliega como otro servicio.

## Estructura

- `main.py`, `chat_access.py` y `config.py`: API, acceso, cupos y configuración.
- `graph.py`, `advisor.py`, `tools.py` y `prompt.py`: agente y herramientas.
- `rag.py`, `store.py` y `lexical.py`: recuperación e índice vectorial.
- `admin_*.py` y `knowledge_*.py`: administración, 2FA, documentos y versiones.
- `manage.py`, `asgi.py`, `db_migrations.py` y `migrations/`: comandos de operación, arranque y esquemas versionados.
- `ingest.py` y `rag-data/`: extracción Word y ubicación local de documentos fuente.
- `scripts/` y `tests/`: diagnóstico y validación.
- `Dockerfile`, `docker/` y `compose.yaml`: contenedor Python independiente.

## Preparación y comandos

Ver [Instructions.txt](Instructions.txt). Desde la carpeta del backend:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Completar .env antes de continuar.
python -m manage db upgrade -d migrations
python -m manage seed-data
python -m manage create-admin "Nombre del admin" admin@tu-dominio.uy --super-admin
python asgi.py
```

El comando de alta también admite los argumentos del ejemplo:

```powershell
python -m manage create-admin "Nombre" correo@tu-dominio.uy contraseña-de-admin true
```

`true` crea un superadministrador; `false`, un administrador. El primer usuario debe ser superadministrador. Las migraciones SQL se versionan con `PRAGMA user_version`, se aplican también al inicializar las bases y preservan los datos existentes. Los administradores anteriores conservan sus permisos como superadministradores.

`seed-data` prepara las carpetas, la primera cuenta configurada por entorno y el índice previo, si existe. No genera contenido de inversión. Los comandos de migración y preparación requieren el backend detenido; la creación de cuentas puede hacerse con el servicio activo.

## Panel y permisos

El acceso web está en **`/admin/login` del frontend**; después de 2FA se usa `/admin/`. Un administrador gestiona conocimiento y su contraseña. Un superadministrador también crea cuentas, modifica roles y consulta auditoría. Cambiar un rol revoca las sesiones del usuario y siempre debe quedar un superadministrador activo.

El backend publica únicamente la API. `/`, `/admin/login`, `/docs`, `/redoc` y `/openapi.json` devuelven 404; las rutas administrativas privadas requieren 2FA. Las rutas desconocidas bajo `/admin/` del frontend devuelven 404.

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
