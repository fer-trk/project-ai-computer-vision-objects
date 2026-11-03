# Aplicación local NOX

Bloque aprobado por Fernanda el 03/11/2026: aplicación local primero; publicación
online aplazada. Reutiliza el análisis de vídeo existente. No se entrena un modelo
ni se declara completado ningún nivel por disponer de una interfaz.

## Inicio

Python 3.11 y FFprobe en PATH; FFmpeg también se necesita para ejecutar las pruebas.
El checkpoint .pt de una clase `nox_texto` debe estar disponible localmente y no
forma parte de Git. Desde la raíz del repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-app.txt
.\.venv\Scripts\python.exe scripts/serve_local.py --model "ruta/al/best.pt"
```

Abrir `http://127.0.0.1:8000`. La interfaz y sus recursos se sirven desde el equipo;
no usan CDN ni servicios externos. El visor Swagger opcional de `/docs` carga sus
recursos desde CDN; el contrato `/openapi.json` siempre está disponible localmente.

La instalación inicial requiere internet. La aplicación utiliza CPU y los pesos
locales; no descarga un modelo alternativo. El launcher escucha únicamente en
127.0.0.1, usa un proceso web y admite un solo análisis simultáneo. Cambiar puerto
con `--port`. Detener con Ctrl+C en la terminal; el análisis activo se interrumpe y
queda registrado como fallido. Cerrar la pestaña del navegador no detiene el servidor.

## Recorrido

1. Seleccionar o arrastrar un vídeo. El umbral predeterminado 0,25 filtra propuestas;
   se puede cambiar antes de subir. No se presenta como precisión ni claridad.
2. Iniciar análisis. La API responde 202 con ID; la pantalla consulta su estado.
3. Revisar el MP4 anotado (sin audio), sus propuestas y el instante de cada una.
4. Descargar MP4, CSV o informe JSON. Los casos sin propuestas son válidos y no
   demuestran ausencia de logos. Los errores se muestran sin inventar resultados.
5. Volver al historial tras cerrar/reiniciar el servidor. Se muestran los 50 análisis
   más recientes; las propuestas se consultan en páginas de hasta 100 registros.

## Persistencia y límites

`local-artifacts/local-app/` contiene `history.sqlite3` y `jobs/<UUID>/`, con entrada,
log del trabajador y resultados. Se guardan estados, parámetros, informe y todas
las propuestas con tiempos, caja, confianza, revisión y soporte. No se generan
recortes individuales ni se clasifica soporte/claridad. Esta entrega no completa T07.
No hay borrado automático; conservar espacio y no subir esta carpeta al repositorio.
La configuración de arranque debe apuntar al mismo `--data-dir` para recuperar el
historial. Un bloqueo de archivo impide usar la misma carpeta desde dos servidores.
Tras un cierre inesperado, trabajos pendientes/en curso pasan a fallidos al reiniciar;
los terminados se conservan y no se reprocesan automáticamente.

Valores iniciales de desarrollo, visibles en pantalla y configurables:

- `--max-upload-mb 100`: tamaño máximo por archivo.
- `--max-duration-seconds 60`: duración máxima del vídeo.
- `--max-pixels 2073600`: superficie máxima de cada frame, admite formato vertical.
- El trabajador dispone de 900 s por análisis. No se promete tiempo real.

Son controles del prototipo local; los límites finales del producto siguen pendientes.
El endpoint web no debe publicarse tal cual. El worker ejecuta el comando existente
como proceso aislado y único; la inferencia no bloquea el bucle HTTP. Los archivos
solo se sirven con ID válido, análisis terminado y un nombre de artefacto permitido.

## API local

- `GET /api/config`: disponibilidad del modelo y límites.
- `POST /api/analyses`: multipart `video` y `confidence`, crea análisis (202).
- `GET /api/analyses`: historial reciente.
- `GET /api/analyses/{id}`: estado, error e informe.
- `GET /api/analyses/{id}/detections?offset=0&limit=50`: propuestas persistidas.
- `GET /api/analyses/{id}/files/video`: reproducción con HTTP Range.
- Artefactos `video`, `csv`, `report`, `frames`, `preview`; añadir `?download=true`.

La API devuelve 409 si ya hay un análisis activo, 413 para tamaño excesivo, 422 para
parámetros o subida vacía y 503 si no hay modelo. Un vídeo ilegible se acepta para
procesamiento y termina con estado failed y un mensaje comprensible, sin resultados
publicados. Las peticiones de navegador deben proceder del mismo origen local.

## Verificación

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
```

La interfaz aún debe utilizarse con el modelo etiquetado como experimental. La
exposición se indica como no calculada: no se suman propuestas como segundos
confirmados ni se muestran porcentajes ficticios. Web pública, autenticación,
medición temporal, recortes y aceptación del modelo siguen pendientes.
