# Despliegue con Coolify

El portal y la API se despliegan desde sus repositorios separados: `invest-lavalleja-frontend` e `invest-lavalleja-backend`. Esta configuración está preparada para un único VPS y una instancia de API; debe validarse en Coolify antes de abrir el servicio al público.

## Preparar el repositorio y los secretos

Extraer el proyecto y revisar los archivos antes de subir el código al repositorio elegido. No subir `.env`, `data/`, copias ni el corpus interno. No se creó ningún repositorio remoto automáticamente.

En un equipo de administración confiable, ejecutar `python scripts/setup_env.py` desde la raíz del repositorio backend. Genera claves distintas para sesión y cifrado en `.env`, sin sobrescribir uno existente y sin imprimir los secretos. Copiar los valores `SECRET_KEY` y `ENCRYPTION_KEY` a **Environment Variables** de Coolify por un canal seguro; no dejar los valores vacíos, de ejemplo o cortos. `SECRET_KEY` debe tener al menos 32 caracteres y `ENCRYPTION_KEY` debe ser una clave Fernet válida. No reutilizar la misma clave para ambas variables.

El log de arranque debe mostrar que `SECRET_KEY` tiene al menos 32 caracteres si el valor configurado no cumple ese mínimo. Reemplazarlo por el valor generado, guardar la variable y volver a desplegar. Mantener ambas claves estables entre despliegues: cambiar `ENCRYPTION_KEY` sin migración impide descifrar datos existentes.

El Compose usa referencias `${VARIABLE}` explícitas para que Coolify las descubra. En Docker local, Compose las toma de `.env`; en Coolify las aporta la configuración del recurso. El contenedor recibe variables de entorno y no requiere copiar el archivo secreto a la imagen. No marcar credenciales como argumentos de build.

Variables mínimas:

```dotenv
APP_ENV=production
SECRET_KEY=<generada por setup_env.py>
ENCRYPTION_KEY=<generada por setup_env.py>
TRUSTED_HOSTS=gianna.tu-dominio.uy,127.0.0.1,localhost
PUBLIC_ORIGINS=https://invest.tu-dominio.uy,https://gianna.tu-dominio.uy
PROXY_HOPS=1
OLLAMA_API_KEY=<tu token>
OLLAMA_MODEL=
EMBEDDING_BACKEND=openvino
```

Los dominios son ejemplos, no direcciones ya creadas. Agregar el origen de la propia API permite utilizar `/chat`. `TRUSTED_HOSTS` usa nombres sin esquema ni puerto; `PUBLIC_ORIGINS` usa esquema y host exactos, con puerto solo cuando forma parte del origen. No utilizar `*`.

## Crear el recurso backend

Crear una Application desde `IntendenciaDeLavalleja/invest-lavalleja-backend`. Seleccionar **Docker Compose**, directorio base `/` y archivo `compose.yaml` en la raíz; usar el modo normal, no Raw Compose. El contexto `build: .` incluye el Dockerfile y `requirements.txt`. No hace falta publicar servicios mediante `ports:`. Si se mantiene el build pack Dockerfile que ya usa la aplicación de Coolify, crear además un volumen persistente montado en `/app/data`; de lo contrario SQLite y el índice se perderán al reemplazar el contenedor.

El Dockerfile incluye `curl` para que el chequeo HTTP de Coolify pueda consultar la salud de la API, además del health check definido en Compose.

En el servicio **api**, establecer el dominio con el puerto interno:

```text
https://gianna.tu-dominio.uy:8000
```

El visitante utiliza HTTPS normal, sin añadir 8000 en la dirección pública. Ese sufijo indica al proxy de Coolify el puerto del contenedor. LanceDB está embebido en la API y no necesita dominio ni puerto propios.

El Compose define `gianna_data:/app/data`. Conserva SQLite, modelos y tablas LanceDB entre redeploys. El health check interno de la API consulta `/health/live`, que no descarga modelos ni llama a un proveedor de pago. Revisar LanceDB desde Diagnóstico una vez iniciada la aplicación.

En el build del portal Astro, definir `PUBLIC_GIANNA_API_BASE=https://gianna.tu-dominio.uy` (sin ruta ni puerto interno). Añadir el origen HTTPS real del portal a `PUBLIC_ORIGINS` del backend. Esta variable pública contiene solo la URL de la API, nunca `OLLAMA_API_KEY`. Después de cambiarla, reconstruir el frontend estático. La configuración de construcción del portal está en `docs/COOLIFY.md` del repositorio frontend. Hasta que haya una versión de conocimiento revisada y publicada, la página de Gianna informará que la base todavía no está disponible.

`PROXY_HOPS=1` solo es correcto cuando el acceso está exclusivamente detrás del proxy de confianza de Coolify. No añadir acceso directo a Internet ni confiar ciegamente en encabezados reenviados. Si existe otro proxy, revisar la cadena y los encabezados efectivos antes de cambiar este valor.

## Inicialización

Desplegar y abrir los logs. Si falta una clave, la aplicación rechaza el arranque en vez de generar un secreto efímero. En la terminal del contenedor **api**, ejecutar:

```bash
flask --app wsgi check-config
flask --app wsgi create-admin
```

Para reproducir el segundo factor por correo del sistema de referencia, configurar SMTP y usar `flask --app wsgi create-admin --mfa email`. El valor predeterminado es TOTP y no requiere SMTP. Entrar en `/admin/login`, resolver el CAPTCHA y completar el segundo factor elegido; con TOTP, guardar la recuperación. Desde ese momento, documentos, indexación, pruebas, usuarios y configuración operativa se manejan en el panel. No existe registro público de administradores ni credenciales iniciales impresas en logs.

En Ajustes, cargar el catálogo real de Ollama y elegir el modelo. Importar el JSON canónico, aprobar, indexar, evaluar y publicar según el manual. Ejecutar `docker compose run --rm api python -m scripts.prepare_models` para la descarga explícita desde Hugging Face. La API usa Ollama para responder y lee los modelos locales.

## Recursos y reproducibilidad

El archivo propone límites de 2 GiB / 2 CPU para API. **Son límites de arranque a comprobar, no consumos medidos ni mínimos garantizados.** Hay un proceso Gunicorn y Bekko y Horizon cargados, compartido por el chat y el trabajador de indexación. La indexación se intercala por lotes, pero puede aumentar la latencia del chat. Programar cargas importantes fuera de horas de atención.

Vigilar memoria al cargar ONNX y al calcular la proyección. Un cierre por OOM requiere aumentar el margen o revisar el perfil; no se soluciona multiplicando workers. El build de dependencias tiene un consumo diferente del servicio en reposo. Conservar espacio para la exportación original, cachés, SQLite, colecciones y copias; no se promete un tamaño final sin descargar el modelo.

Las revisiones de Bekko y Horizon están fijadas en `gianna/services/neural.py` y los artefactos se verifican con SHA-256. Mantener versiones del modelo y paquetes coherentes. No cuantizar o cambiar pooling sin crear una nueva base vectorial y medir la pérdida de recuperación.

## Verificación de apertura

Probar desde una sesión sin autenticar que `/admin/bases` no revela información. Probar desde otro origen que la API pública lo rechaza. Confirmar que el volumen LanceDB no se publica como archivos estáticos. Reiniciar y comprobar persistencia, luego ejecutar las preguntas de evaluación y una conversación real de seguimiento.

Si aparece “No Available Server”, revisar health, logs, dominio con puerto interno, escucha `0.0.0.0:8000`, certificados y hosts permitidos. No desactivar autenticación, CSRF o validación de hosts para ocultar el problema.

Referencia oficial consultada el 28/09/2026: https://coolify.io/docs/applications/builds/docker-compose
