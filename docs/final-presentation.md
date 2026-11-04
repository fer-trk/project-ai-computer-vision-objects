# Presentación final: guion y lista de ensayo

Estado: **borrador para revisión**. Resume el guion de una exposición de 10 minutos y la lista de comprobación de la demo en vivo. No añade resultados nuevos y no declara ningún nivel como completado. Las cifras proceden de documentos y registros ya publicados, y se indica su fuente.

## Formato

- 10 diapositivas para exponer, unos 10 minutos, más 5 de anexo para preguntas.
- Responde a lo que pide el [briefing](assignment.md): objetivos, desarrollo, tecnologías, demo en vivo y gestión del proyecto.
- Guion hablado para dos personas, con tiempos y reparto: [final-presentation-script.md](final-presentation-script.md).
- La presentación en sí, sus capturas y su PDF se conservan **fuera de Git**. Ver la sección de archivos externos.

## Guion por diapositiva

| N.º | Título | Tiempo | Mensaje clave |
| --- | --- | --- | --- |
| 1 | Portada | 0:30 | Prueba de concepto para NOX en pádel. Prototipo local con modelo experimental. |
| 2 | Qué pide el brief | 1:00 | Entrenar, analizar vídeo, informar de tiempo y porcentaje, y guardar detecciones. |
| 3 | Qué medimos y qué cuenta | 0:45 | Ropa y palas primero. Solo cuentan los logos claros. El cálculo de segundos y porcentaje está pendiente. |
| 4 | Tecnologías | 0:45 | YOLO11n, PyTorch, PyAV, FFmpeg, FastAPI, SQLite, GitHub Actions. Coste cero. |
| 5 | Datos y entrenamiento | 1:00 | 23 imágenes, 21 cajas, un lote pequeño. Controles contra fugas y repeticiones. |
| 6 | Resultados, sin maquillar | 1:00 | El proceso aprende, pero el modelo no está aceptado. |
| 7 | Demo en vivo | 2:30 | Cargar un vídeo local, analizar, reproducir, descargar. |
| 8 | Calidad de ingeniería | 0:45 | Ramas cortas, PR, CI y Kanban. |
| 9 | Niveles del brief | 0:45 | Estado real por nivel, sin inflarlo. |
| 10 | Siguientes pasos | 0:45 | Permisos, nuevo entrenamiento, medición de exposición, más marcas y nube. |
| 11 a 15 | Anexos | Preguntas | Arquitectura, resultado de un análisis, uso, opciones y datos y derechos. |

## Cifras citadas y su fuente

| Cifra | Fuente |
| --- | --- |
| 23 imágenes, 21 cajas, particiones 19, 3 y 1 | [Dataset y particiones](nox-text-dataset-2026-11-03.md) |
| 4 entrenamientos reales en Colab | Historial de la issue de T05 |
| mAP50 de 0 en validación, 0 aciertos, 1 falso positivo y 3 omisiones en 4 imágenes | Ensayo completo del 3 de noviembre, issue de T05 |
| 137 pruebas correctas en CI | README de `main` y la issue de T02 |
| 7,17 s, 215 fotogramas, 107 propuestas y 70,36 s | [Registro de validación de Mozart](local-app-validation-2026-11-03.json) |
| 78,95 s con los mismos 215 fotogramas y 107 propuestas | Ensayo local del 4 de noviembre, historial de Mozart. No está versionado. |
| Límites de 100 MiB, 60 s y 2.073.600 píxeles | [Aplicación local](local-app.md) |

## Qué no se afirma

- Ningún nivel del briefing se da por completado.
- Las 107 propuestas no son 107 aciertos, y la confianza del modelo no es precisión.
- No hay medición de segundos ni porcentaje de exposición, ni detector multimarca, ni API en la nube.
- El vídeo de la demo comparte un fotograma con el entrenamiento: no es una evaluación independiente.
- El test actual es una sola imagen ya inspeccionada, y no demuestra que el detector generalice.

## Demo en vivo: comprobaciones antes de ensayar

1. **Checkpoint:** el SHA-256 del `best.pt` debe ser `b69c4a576d62a464ba9f27f3754e7a6df90ced79afd7e87b93f8dd22fbbfa171`. Modelo experimental, sin calidad aceptada.
2. **Vídeo:** usar uno local con uso autorizado. Los permisos del vídeo histórico `7700661233569041687.mp4` siguen **pendientes de documentar**. Sin esa constancia, usar otro vídeo.
3. **Herramientas:** Python 3.11, dependencias de `requirements-app.txt` y FFmpeg y FFprobe en el PATH.
4. **Arranque**, desde la raíz del clon:

   ```powershell
   .\.venv\Scripts\python.exe scripts/serve_local.py --model "local-artifacts/demo/models/best.pt" --data-dir "local-artifacts/demo/history"
   ```

5. **Recorrido:** abrir `http://127.0.0.1:8000`, elegir **Desde mi equipo**, lanzar un análisis nuevo, reproducir el resultado, consultar las propuestas y descargar CSV o JSON.
6. **Tiempos:** un vídeo de 7 s tardó entre 70 y 79 s. No se procesa a la velocidad de reproducción. Ensayar en el equipo de la presentación.
7. **Respaldo:** no usar el enlace de TikTok, porque la descarga puede fallar. Tener capturas de las pantallas que no muestran fotogramas del vídeo.

## Estilo visual

Coincide con la interfaz de Mozart.

| Elemento | Valor |
| --- | --- |
| Fondo claro | `#FFF8F3` |
| Fondo oscuro | `#281D17` |
| Acento naranja | `#FF8B42`, solo en formas y puntos; para texto sobre claro, `#B8500C` |
| Texto principal | `#33251D` |
| Aviso de modelo experimental | fondo `#FFF0DD`, borde `#F2D9B9`, texto `#8A5B2D` |

## Archivos externos a Git

No se versionan: la presentación, su PDF, las capturas de pantalla, el checkpoint, el vídeo de la demo ni el historial local de Mozart. El permiso de uso del vídeo y la distribución segura de estos archivos requieren acuerdo previo, según las reglas del proyecto.

## Pendientes antes de presentar

- Confirmar por escrito el permiso de uso del vídeo, o elegir otro autorizado.
- Completar los nombres del equipo en la portada.
- Ensayar la demo completa en el ordenador de la presentación.
- Decidir con Fer si el esencial limitado, el Plan B del [runbook de T04](t04-essential-runbook.md), se menciona como opción.
