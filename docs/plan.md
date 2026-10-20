# Plan de entrega y backlog

Estado: propuesta. Ocho días hábiles; fecha de inicio y dedicación diaria pendientes. Sin compromiso de fechas calendario hasta acordarlas. El aprendizaje y la revisión están incluidos.

## Secuencia

| Día | Resultado verificable |
| --- | --- |
| 1 | Revisar specs y decisiones, comprobar hardware, seleccionar marcas/datos, configurar repositorio y Kanban. Probar viabilidad del hosting gratuito con inferencia mínima; si no es viable, decidir alternativa ese día. |
| 2 | Preparar y revisar anotaciones/particiones, fijar entorno y ejecutar primer entrenamiento. |
| 3 | Demostrar nivel esencial y comenzar/ampliar el entrenamiento multimarca; congelar un baseline reproducible. |
| 4 | Vídeo anotado y medición temporal probada; demostrar nivel medio. |
| 5 | Persistencia de detecciones/recortes, confianza y evaluación multimarca; demostrar nivel avanzado. |
| 6 | Integrar web, API y despliegue gratuito; probar recorrido completo y demostrar nivel experto. Congelar funcionalidades. |
| 7 | Corregir fallos, completar evaluación independiente y comprobar instalación/deploy reproducibles. |
| 8 | Finalizar README, presentación y demo; ensayo y revisión final del portfolio. |

Los días 7 y 8 se reservan para calidad y entrega. Al final de cada jornada: evidencia, bloqueo principal, tiempo restante y decisión de alcance si hace falta. Experticia profesional es el horizonte; el nivel experto de la consigna es un entregable específico.

## Backlog publicado

[Tablero de seguimiento](https://github.com/users/fer-trk/projects/1): catorce tarjetas operativas. La estructura del backlog está aprobada; las specs funcionales y decisiones técnicas conservan los pendientes de revisión. Publicar no significa iniciar ni completar una tarea.

| Orden | ID estable | Nivel | Entregable | Depende de |
| --- | --- | --- | --- | --- |
| 1 | T01 | Preparación | [Acordar alcance y decisiones iniciales](https://github.com/fer-trk/project-ai-computer-vision-objects/issues/1) | — |
| 2 | T02 | Preparación | [Configurar entorno reproducible y controles del repositorio](https://github.com/fer-trk/project-ai-computer-vision-objects/issues/2) | T01 |
| 3 | T03 | Preparación | [Verificar recursos y viabilidad del servicio gratuito](https://github.com/fer-trk/project-ai-computer-vision-objects/issues/3) | T01 |
| 4 | T04 | Esencial | [Preparar datos y anotaciones de marcas](https://github.com/fer-trk/project-ai-computer-vision-objects/issues/4) | T01, T03 |
| 5 | T05 | Esencial | [Reentrenar un detector para la primera marca](https://github.com/fer-trk/project-ai-computer-vision-objects/issues/5) | T03, T04 |
| 6 | T10 | Esencial | [Evaluar la primera marca y demostrar detección en imágenes](https://github.com/fer-trk/project-ai-computer-vision-objects/issues/10) | T05 |
| 7 | T06 | Medio | [Procesar vídeos y visualizar detecciones](https://github.com/fer-trk/project-ai-computer-vision-objects/issues/6) | T10 |
| 8 | T11 | Medio | [Calcular tiempo y porcentaje de exposición por marca](https://github.com/fer-trk/project-ai-computer-vision-objects/issues/11) | T06 |
| 9 | T12 | Avanzado | [Ampliar y evaluar el detector multimarca](https://github.com/fer-trk/project-ai-computer-vision-objects/issues/12) | T04, T10, T11 |
| 10 | T07 | Avanzado | [Persistir ejecuciones, detecciones y recortes](https://github.com/fer-trk/project-ai-computer-vision-objects/issues/7) | T11, T12 |
| 11 | T08 | Experto | [Exponer el análisis mediante una API documentada](https://github.com/fer-trk/project-ai-computer-vision-objects/issues/8) | T07 |
| 12 | T13 | Experto | [Crear la aplicación web de carga y resultados](https://github.com/fer-trk/project-ai-computer-vision-objects/issues/13) | T08 |
| 13 | T14 | Experto | [Desplegar y verificar la aplicación y API gratuitas](https://github.com/fer-trk/project-ai-computer-vision-objects/issues/14) | T03, T08, T13 |
| 14 | T09 | Entrega | [Validar la entrega y presentar el portfolio](https://github.com/fer-trk/project-ai-computer-vision-objects/issues/9) | T02, T14 |

Cada issue contiene pasos verificables, criterios de aceptación, aprendizaje y registro de decisiones/bloqueos/evidencia. Los requisitos se mantienen en specs.md y el historial de ejecución en la issue. Conservar los IDs y URLs existentes; el campo Orden muestra la secuencia tras el desglose. Una tarea puede originar correcciones justificadas, sin cerrar o duplicar trabajo para aparentar avance.
## Flujo y definición de terminado

Estados: Pendiente → Preparado → En curso → En revisión → Hecho. Una sola tarea en curso. Bloqueos se señalan con etiqueta y motivo, sin inventar un estado de éxito.

- Preparado: objetivo educativo, alcance, criterios y decisiones necesarias revisados por el usuario.
- En curso: rama de tarea activa, creada desde `main` actualizado.
- En revisión: PR con issue enlazada, evidencia y CI; el usuario puede explicar las decisiones.
- Hecho: criterios demostrados, revisión del usuario, comprobaciones aprobadas, documentación pertinente y PR integrado. Cerrar issue y eliminar rama.
- CI y revisión humana son condiciones diferentes. Si la cuenta no permite imponer alguna protección, documentar la limitación y aplicar el control operativo sin afirmar que está bloqueado técnicamente.
- Commit: Conventional Commits. Squash recomendado, conservando validación de todos los commits del PR y su título; no crear commits ni ramas hasta acordar el primer bloque.

La especificación contiene requisitos; la issue conserva ejecución y decisiones. No mantener copias paralelas del mismo historial. Tras publicar el backlog, añadir enlaces a las issues en esta tabla.

## Organización por niveles

| Nivel | Tarjetas | Cantidad |
| --- | --- | --- |
| Preparación | T01, T02, T03 | 3 |
| Esencial | T04, T05, T10 | 3 |
| Medio | T06, T11 | 2 |
| Avanzado | T12, T07 | 2 |
| Experto | T08, T13, T14 | 3 |
| Entrega | T09 | 1 |

Las vistas Kanban conservan los cuatro niveles de las consignas y el tablero general. T03 prueba viabilidad cloud pronto; T14 realiza el despliegue completo. Los estados y checkboxes se actualizan con evidencia real y revisión del usuario; no se cierran tareas por mera planificación. Registrar decisiones y bloqueos en la issue en el momento en que ocurren. Los días 7 y 8 siguen reservados para calidad y entrega.
