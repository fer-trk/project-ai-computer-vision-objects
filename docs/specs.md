# Especificaciones funcionales

Estado: borrador para revisión. Las propuestas no son decisiones aprobadas.

## Objetivo y restricciones

Una empresa de publicidad necesita medir la exposición visual de marcas en vídeos. El sistema detectará logos, localizará sus apariciones y presentará segundos y porcentaje de exposición por marca, con detecciones persistidas.

Contexto de demostración propuesto por el usuario: partidos o material relacionado con pádel. Marcas pendientes de selección; empezar con una y extender a al menos dos. No se presupone permiso para descargar o redistribuir retransmisiones.

- Plazo máximo: ocho días hábiles, incluida gestión, aprendizaje, pruebas y presentación. Inicio y horas disponibles por día pendientes. No contar con ampliación.
- Coste financiero: cero. Verificar licencias, cuotas y ausencia de cargos automáticos antes de adoptar servicios. Sin entrenamiento pesado en CI.
- Meta: nivel experto, demostrando también cada nivel anterior. No declarar experto si falta cloud/API.
- Proceso: bloques pequeños revisados por el usuario; estructura ampliable sin construir infraestructura especulativa.
- Fuente: `assignment.md`. El usuario confirma que el roadmap enlazado no añade requisitos; no es necesario investigarlo.

## Contexto de pádel y demo acordada en conversación

Registro de la conversación del 20 de octubre de 2026; las specs completas siguen siendo borrador. El usuario quiere analizar logos en ropa, palas y elementos de pista. La exposición de patrocinadores en ropa es una prioridad de interés. No limitar el dataset ni las pruebas a vallas; revisar ejemplos de cada soporte y documentar dificultad y resultados sin prometer detectar logos ilegibles.

- Fuente candidata indicada por el usuario: vídeos de la cuenta premierpadel de TikTok. No se ha seleccionado ni descargado material; comprobar disponibilidad de descarga y permisos para entrenamiento, demo y publicación antes de utilizarlo. Vídeos y recortes no se incorporan automáticamente al repositorio público.
- El entrenamiento seguirá utilizando imágenes anotadas, que pueden ser frames extraídos de vídeos utilizables. Conservar el origen para separar particiones por vídeo/sesión sin fuga de datos.
- Demo solicitada: resaltar las detecciones y listarlas con su momento y duración en el vídeo. Propuesta compatible con las consignas: cajas rectangulares con clase y confianza, y tabla de apariciones con inicio/fin en mm:ss y duración en segundos. La lista de eventos agrega intervalos según la política temporal, no presenta cada frame como una aparición independiente.
- Medir exposición de marca en ropa no identifica automáticamente al jugador ni atribuye la exposición a un patrocinio personal. Atribución por jugador y clasificación automática del soporte (ropa/pala/pista) quedan pendientes de decisión; no se incorporan silenciosamente como obligaciones adicionales.
- Ampliación sugerida por el usuario: porcentaje de pantalla ocupado por el logo. No es un requisito de los niveles de las consignas ni se compromete dentro de los ocho días antes de revisar prioridades.
- Si se acuerda esa ampliación, el área de la caja dividida por el área del frame permite estimar ocupación en imagen, no el área exacta del logo. Definir unión espacial para cajas solapadas, agregación por marca, promedio/pico y denominador temporal antes de implementar. Separarlo del porcentaje de duración de exposición.
- Decisiones abiertas: marcas concretas, ejemplos y derechos de vídeos, medición por marca o atribución a jugador, tolerancia temporal y eventual alcance de ocupación. No iniciar descarga, anotación o entrenamiento por este registro.

## Flujo principal

1. Obtener imágenes utilizables, anotar logos y preparar particiones independientes.
2. Reentrenar un detector preentrenado para las marcas acordadas y evaluar con datos reservados.
3. Subir un vídeo compatible y validar que puede procesarse dentro de los límites publicados.
4. Analizar el vídeo con el modelo seleccionado, mostrando cajas, nombre y confianza.
5. Guardar detecciones y recortes asociados al vídeo y la ejecución.
6. Consultar resultados y un informe por marca con tiempo y porcentaje de exposición.
7. Acceder a la misma capacidad mediante una API desplegada en cloud y demostrarla desde un cliente independiente.

## Requisitos y aceptación

| ID | Nivel | Requisito y evidencia de aceptación |
| --- | --- | --- |
| RF-01 | Esencial | Reentrenar un modelo preentrenado con imágenes anotadas para una marca nueva. Guardar configuración, clases, origen del checkpoint y evidencia del entrenamiento; usar solo inferencia genérica no cumple. |
| RF-02 | Esencial | En una imagen de evaluación, mostrar la caja del logo detectado. Registrar también resultados en imágenes sin la marca y fallos conocidos. |
| RF-03 | Medio | Procesar un archivo de vídeo y mostrar el nombre de clase debajo de cada caja, manteniendo su correspondencia con la detección. |
| RF-04 | Avanzado | Mostrar junto a la clase la confianza del detector, entre 0 y 100 %. Explicar que no garantiza exactitud ni es una probabilidad calibrada. |
| RF-05 | Avanzado | Persistir detecciones con vídeo, ejecución, marca, timestamp, caja, confianza, recorte y categoría de evidencia; distinguir hipótesis sin duración de las apariciones claras. Recuperar esos datos tras reiniciar; verificar referencias y recortes legibles. |
| RF-06 | Avanzado | Un mismo detector reconoce al menos dos marcas. Evaluar y guardar resultados separados, incluyendo un caso con ambas marcas simultáneas. |
| RF-07 | Briefing | Generar informe con duración total del vídeo, segundos y porcentaje de exposición clara detectada por marca, parámetros usados y versión del modelo; las hipótesis se muestran aparte sin medición temporal. Un vídeo sin detecciones produce un informe válido con ceros. |
| RF-08 | Experto | Aplicación web para subir vídeos, conocer el estado del análisis y visualizar resultados e informe. Mostrar errores comprensibles para archivos inválidos o límites excedidos. |
| RF-09 | Experto | Modelo servido en cloud mediante API documentada, accesible desde otro cliente. Probar un vídeo válido y entradas inválidas; publicar límites y comprobar coste cero. Ejecutar todo localmente no satisface este requisito. |
| RF-10 | Entrega | Repositorio documentado con instalación reproducible, ramas operativas y commits convencionales; Kanban actualizado, demo en vivo y presentación técnica. |

## Política de claridad y contabilización

Decisión explícita del usuario, 20 de octubre de 2026: la herramienta se centra en apariciones claras y posibles identificaciones. Una jugada rápida puede contener muchos instantes no identificables; no se fuerza una marca en ellos.

| Categoría por detección | Presentación | Medición temporal |
| --- | --- | --- |
| 1. Logo claro e identificable | Caja, marca y confianza; evento de exposición clara. | Sí: solo sus intervalos aportan segundos y porcentaje. |
| 2. Logo parcialmente visible con hipótesis de marca | Caja y etiqueta explícita «Posible marca X — no contabilizada», con confianza diferenciada de certeza. | No: no calcular ni mostrar duración o porcentaje para la hipótesis; puede conservarse el instante como referencia. |
| 3. Evidencia insuficiente para identificar marca | Descartar de la lista de marcas y del informe de exposición; no inventar una hipótesis. | No. |

- La clasificación se aplica a cada candidato, no a todo el frame: un logo claro de una valla puede contabilizarse aunque otro en una pala sea ilegible en el mismo instante.
- El informe principal se denomina exposición clara detectada por marca. El porcentaje utiliza la duración total del vídeo como denominador; descartar frames difíciles no reduce ese denominador.
- Una secuencia clara → probable/no identificable → clara contiene intervalos contables separados. No sumar ni rellenar el tramo incierto mediante continuidad del objeto, patrocinio conocido o hipótesis de identidad.
- Persistir el estado de evidencia y la versión de la regla utilizada. Para hipótesis guardar la marca candidata, confianza, recorte e instante si existe; duración de exposición no aplicable, nunca una duración medida de cero que parezca una observación confirmada.
- Mostrar resultados claros e hipótesis en grupos distinguibles. Un vídeo con solo hipótesis tiene cero exposición clara detectada y una lista de posibles marcas, no una afirmación de ausencia real.
- La confianza del detector por sí sola no define la claridad. El mecanismo de clasificación, los ejemplos de referencia y los umbrales quedan pendientes de revisión con el usuario y validación en datos reservados; no fijar valores numéricos arbitrarios ni asumir certeza visual por confianza alta.
- Verificar explícitamente: solo claros; solo hipótesis; solo no identificables; mezcla de categorías en un frame; cambio clara/probable/clara; instancias simultáneas de la misma marca. Conservar métricas y errores de clasificación de claridad además de la evaluación del detector, sin exigir un clasificador adicional antes de acordar diseño.

## Medición temporal propuesta

Pendiente de revisión antes de implementar RF-07.

- Usar timestamps reales y duración del vídeo; no asumir frecuencia constante sin verificarla.
- En el modo base procesar todos los frames. Solo cada detección de categoría 1 (clara) de una marca acredita el intervalo desde el timestamp del frame hasta el siguiente, acotado a la duración; el último termina en la duración del vídeo.
- Sumar la unión de intervalos por marca. Dos logos de la misma marca simultáneos no duplican segundos. Marcas diferentes se computan de forma independiente; sus porcentajes pueden sumar más de 100 %.
- `exposure_percentage = 100 * exposure_seconds / video_duration_seconds`. Rechazar duración cero o indeterminable sin un método válido de cálculo.
- Publicar el umbral de confianza y los filtros. No interpolar huecos ni contar marcas por debajo del umbral sin una regla acordada.
- Si el hardware obliga a muestrear frames, acordar antes la estimación, granularidad y limitaciones. Mostrarla explícitamente como estimación, no como tiempo exacto observado.
- Verificar con un vídeo controlado: una marca durante un intervalo conocido, dos instancias simultáneas, dos marcas, ausencia de marcas y último frame. Acordar tolerancia antes de ejecutar la prueba.

## Datos, entrenamiento y evaluación

- Registrar fuentes, licencias y permisos de imágenes, vídeos, pesos y bibliotecas antes de usarlos o distribuirlos.
- Anotar cajas y nombres consistentes. Separar train/validation/test por vídeo o sesión de origen; no repartir frames casi idénticos entre particiones.
- Aplicar resizing, normalización/escalado conforme al modelo; documentar aumentos (flip, crop, color jitter) pertinentes. Evitar que un crop deje etiquetas inválidas o que transformaciones destruyan la utilidad de un logo.
- Mantener test reservado: no elegir el umbral ni ajustar el entrenamiento con él. Versionar manifiesto de datos, configuración, semilla y artefacto del modelo.
- Informar precisión, recall y mAP por clase con definición del umbral IoU; ejemplos de falsos positivos y negativos y tiempo de proceso en el hardware real. Acordar objetivos numéricos tras el primer baseline, antes de la evaluación final.
- Evaluar logos pequeños, desenfoque, oclusión, cambios de iluminación y presencia de marcas no entrenadas. Una demo seleccionada no sustituye al conjunto de evaluación.

## Contratos mínimos propuestos

- Vídeo: identificador, nombre original, duración válida, metadatos técnicos y referencia al archivo.
- Ejecución: identificador, vídeo, estado, versión del modelo, configuración, inicio/fin y error si falla.
- Detección: ejecución, clase candidata, categoría de evidencia, regla aplicada, timestamp/frame, coordenadas, confianza y referencia al recorte persistido; las hipótesis no tienen duración de exposición. Proteger la coherencia entre BD y archivos.
- Informe: ejecución, marca, intervalos unidos, segundos y porcentaje. Repetir un análisis crea una ejecución distinguible.
- Guardar recortes como archivos duraderos con referencia en BD es una propuesta; revisar si la evaluación exige binarios en la propia BD.
- Front y API reutilizan el mismo núcleo de inferencia e informe. No duplicar la lógica ni introducir microservicios sin necesidad.
- Formatos, tamaño/duración máximos, tiempo límite, retención de archivos y contrato API se acuerdan tras medir recursos. Publicarlos y probar el rechazo de entradas fuera del contrato.
- No exponer rutas internas o secretos; validar contenido y nombres, aislar archivos por ejecución y limitar uso de recursos. Acordar protección frente a abuso antes de hacer público el servicio gratuito.

## Alcance y decisiones abiertas

Hardware observado el 20 de octubre de 2026: 7,8 GiB de RAM, Intel Core i5-8365U (4 núcleos/8 hilos) e Intel UHD Graphics 620 integrada. Propuesta: desarrollo y pruebas pequeñas por CPU en local; entrenamiento de un detector pequeño en una sesión gratuita de Colab con GPU, sujeto a disponibilidad. RAM y GPU cumplen funciones distintas: la primera sostiene datos/procesos; la segunda acelera entrenamiento. No comprar hardware. Medir memoria y latencia antes de fijar resolución, batch y duración de vídeos; procesar frames progresivamente sin cargar el vídeo completo en RAM.

Colab no garantiza GPU ni recursos constantes y no sustituye un hosting de API. Guardar checkpoints recuperables y comprobar acceso el primer día. Si no hay GPU, medir un entrenamiento mínimo por CPU y acordar la alternativa sin suponer una extensión. Referencia: [límites oficiales de Colab](https://research.google.com/colaboratory/intl/es/faq.html).

Fuera del alcance inicial: gestión de clientes, facturación, reconocimiento de jugadores, predicción comercial y entrenamiento automático desde la web.

Decidir con el usuario: marcas y fuentes; hardware y horas disponibles; stack/modelo y licencias; objetivos de evaluación; contrato temporal; almacenamiento; hosting gratuito y límites; formato de exportación si se necesita.

Las consignas permiten análisis offline pero mencionan detección en tiempo real en evaluación. Mantenerlo como ambigüedad explícita; proponer una demostración de velocidad sin añadir streaming obligatorio. El usuario debe resolver esta interpretación antes de cerrar alcance.

Si plazo o recursos amenazan un requisito obligatorio, comunicar el bloqueo y alternativas. Reducir extras o tamaño de demo con acuerdo; no eliminar silenciosamente niveles ni sustituir entrenamiento o cloud por una simulación.


