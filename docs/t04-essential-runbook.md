# T04 — Ruta hacia el nivel esencial (runbook)

Estado: **borrador de planificación**. Revisión documental y fusión aprobadas por Fer el 04/11/2026; esta aprobación no elige un plan ni autoriza la reducción de alcance del Plan B. El documento no contiene resultados nuevos, no aprueba umbrales y no cierra T04, T05 ni T10. Las cifras citadas proceden de documentos ya publicados y se indican con su fuente.

## Punto de partida (sin cambios)

- Lote real vigente: 23 imágenes (17 positivas, 6 negativas, 21 cajas `nox_texto`), con la partición exploratoria de [nox-text-dataset-2026-11-03.md](nox-text-dataset-2026-11-03.md). Su test es **una sola imagen** ya inspeccionada: no es un test ciego.
- Permisos de reutilización de las fuentes: **pendientes de documentar**. Identidad de partidos/sesiones: provisional.
- Único entrenamiento realizado: ensayo mínimo de tres épocas con un solo positivo en validación ([nox-first-training-review-2026-10-27.md](nox-first-training-review-2026-10-27.md)). No demuestra calidad general y no debe sustituirse por métricas de otra ejecución.
- Requisitos del nivel (specs): **RF-01** reentrenar un modelo preentrenado con imágenes anotadas para una marca nueva, guardando configuración, clases, origen del checkpoint y evidencia; **RF-02** mostrar la caja del logo detectado en imágenes de evaluación y registrar resultados en imágenes sin la marca y fallos conocidos.

## Datos sintéticos de la PR #17: solo diagnóstico

El conjunto sintético del [PR #17](https://github.com/fer-trk/project-ai-computer-vision-objects/pull/17), ya integrado en `dev`, sirve únicamente para comprobar el pipeline y estudiar si el modelo aprende un patrón controlado.

- **No se mezcla** con el dataset oficial de T04: ni en `train`, `val` ni `test`, ni como aumento o relleno de negativos.
- **No entra** en ninguna métrica publicada ni en la evaluación de T05/T10. Un buen resultado sobre él no es evidencia de fiabilidad.
- No se sube a Roboflow ni sustituye imágenes reales.
- La referencia versionada (manifiesto, YAML y etiquetas) se conserva en `data-synthetic/nox-text-diagnostic/`. El generador escribe el conjunto completo en `local-artifacts/nox-text-diagnostic/`, ignorado por Git, sin sobrescribir la referencia. Sus particiones propias siguen siendo `diag_train`/`diag_val`.

## Plan A — esencial completo con datos reales

Orden de trabajo; no pasar al siguiente paso sin evidencia del anterior. Cada decisión se registra en la issue correspondiente.

1. **Revisar el lote real de T04.** Reinspeccionar cajas y decisiones a escala nativa. Separar positivos claros, negativos revisados y ambiguos; los ambiguos quedan fuera del entrenamiento. Ampliar con más originales variados si Fer lo aprueba (la guía de variantes propone una tanda inicial de unas 50; 200–300 es objetivo de recopilación, no umbral de calidad).
2. **Validar permisos, anotaciones y procedencia.** Para cada fuente: enlace, vídeo/sesión, instante o frame, hash, dimensiones, estado de permiso/licencia. Si el permiso no consta, la fuente no se usa para entrenar ni publicar. Aceptación humana de las cajas registrada.
3. **Separar `train`/`val`/`test` por vídeo o sesión.** Sin frames cercanos del mismo plano repartidos entre particiones. Reservar **al menos un origen independiente real para `test`**. La ausencia de hashes duplicados no prueba independencia. El test no se usa para decidir etiquetas, aumentos ni configuración.
4. **Entrenar un único modelo `nox_texto`** (clase 0), partiendo de un checkpoint preentrenado, sin gastos y dentro de los recursos gratuitos verificados en T03. Guardar configuración, semilla, versión de dependencias, origen del checkpoint y evidencia. Los pesos no se versionan en Git.
5. **Evaluar en el test real reservado**, una vez fijada la configuración. Incluir imágenes sin la marca.
6. **Registrar resultados:** métricas con su definición (precisión, recall, mAP50, mAP50–95 y umbral de confianza usado), número de imágenes y cajas del test, falsos positivos, falsos negativos (con ejemplos a escala nativa) y límites (tamaño del test, tipos de soporte, condiciones no cubiertas). Ropa/palas y soportes estáticos se informan por separado.

## Plan B — esencial limitado

Solo si Plan A no es viable en plazo o con las fuentes disponibles.

- Alcance reducido a `nox_texto`.
- **Solo imágenes fijas y primeros planos claros.**
- **Excluidos:** `nox_simbolo`, segunda marca, vídeo y exposición temporal.
- Se declara **"esencial limitado"** únicamente si **Fer lo aprueba** explícitamente **y** el test real lo respalda. Es una reducción de alcance: debe quedar documentada en la issue y en el informe final, sin presentarla como cumplimiento del multimarca ni del nivel medio.
- Mantiene las condiciones del Plan A para permisos, partición por origen, test reservado y registro de fallos.

## Checklist de aceptación

Marcar cada punto solo con evidencia enlazada en la issue.

- [ ] Permisos o licencias de cada fuente documentados; fuentes sin permiso excluidas.
- [ ] Cajas y decisiones revisadas a escala nativa y aceptadas por una persona.
- [ ] Procedencia completa (fuente, vídeo/sesión, instante, hash, dimensiones) en el manifiesto.
- [ ] Particiones por vídeo o sesión, con grupos de origen disjuntos y un origen real independiente reservado para `test`.
- [ ] Ningún dato sintético en las particiones ni en las métricas oficiales.
- [ ] Umbrales de calidad definidos y aprobados por Fer **antes** de evaluar.
- [ ] Un único modelo `nox_texto` reentrenado con configuración, checkpoint de origen y evidencia guardados (RF-01).
- [ ] Evaluación en test real reservado, con imágenes sin la marca (RF-02).
- [ ] Caja detectada mostrada sobre imágenes de evaluación.
- [ ] Métricas con definición, falsos positivos, falsos negativos y límites registrados.
- [ ] Sin imágenes, ZIP, pesos ni datos de usuario en Git.
- [ ] Decisión de Fer registrada (Plan A completo o Plan B limitado).

## Esencial pendiente: criterios

El esencial **se declara pendiente** (no cumplido ni "limitado") si ocurre cualquiera de estos casos:

- No hay permisos o procedencia suficientes para el material real usado.
- No existe un origen real independiente reservado para `test`, o el test se usó para decidir etiquetas, aumentos o configuración.
- El test real no alcanza los umbrales aprobados por Fer, o no existe evidencia en imágenes sin la marca.
- El resultado depende de datos sintéticos, de una única imagen de test o de una partición sin independencia verificada.
- Faltan el registro de configuración y checkpoint de origen, o los falsos positivos y negativos no se han documentado.
- Fer no aprueba la reducción de alcance del Plan B.

En ese caso se documentan resultados y límites tal cual, se registra el bloqueo en la issue y se decide el siguiente paso con Fer; no se cierran T04, T05 ni T10 ni se reinterpretan las métricas.

## Fuera de esta rama

No modifica la PR #17, no añade datos ni resultados y no abre ni cierra issues.
