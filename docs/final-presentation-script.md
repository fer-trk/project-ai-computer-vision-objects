# Guion de 10 minutos: El Mozart

Dos personas exponen: **A** y **B**. Sustituye A y B por los nombres reales. Sigue las diapositivas 1 a 10 de la presentación. Duración total: unos 9:45, con margen para la espera del análisis en la demo.

## Reparto

| Persona | Diapositivas | Tiempo aproximado |
| --- | --- | --- |
| A | 1, 2, 3, 4, 9 y el final de la 10 | 4:00 |
| B | 5, 6, 8 y el inicio de la 10 | 3:00 |
| A y B | 7 (demo: A maneja, B comenta) | 2:30 |

## 1. Portada · 0:00 a 0:30 · A

> Buenos días. Somos [Nombre A] y [Nombre B], y os presentamos El Mozart: una prueba de concepto para medir cuánto tiempo aparece el logo de una marca, NOX, en vídeos de pádel. Es un prototipo funcional con un modelo todavía experimental, y os contaremos también lo que no funciona.

## 2. Qué pide el brief · 0:30 a 1:30 · A

> El brief pide cuatro cosas: entrenar un modelo que detecte una marca nueva, analizar un vídeo y decidir si aparece, informar de cuánto tiempo y qué porcentaje del vídeo, y guardar las detecciones en una base de datos. Lo organiza en cuatro niveles, de esencial a experto: detectar en imagen, funcionar en vídeo, mostrar la confianza y guardar datos, y por último web y nube. Es una prueba de concepto, así que no hace falta tiempo real. Antes de programar tuvimos que decidir qué cuenta como exposición.

## 3. Qué medimos y qué cuenta · 1:30 a 2:15 · A

> Nuestra prioridad son los logos en ropa y palas de los jugadores. Carteles y red van aparte, en una sección secundaria. Solo cuentan los logos claramente identificables. Si el logo se ve a medias y sospechamos la marca, se muestra como posible pero no suma tiempo. Si no se puede identificar, se descarta. El porcentaje se calcula sobre la duración total del vídeo. Ojo: esta regla está definida, pero Mozart todavía no calcula segundos ni porcentaje.

## 4. Tecnologías · 2:15 a 3:00 · A

> Usamos YOLO11n con Ultralytics y PyTorch, entrenado en Colab con GPU gratuita. El vídeo se lee con PyAV y FFmpeg y se procesa en CPU. La aplicación es una interfaz local con una API en FastAPI y una base SQLite para el historial. Gestionamos el proyecto con GitHub, con pruebas automáticas y un tablero Kanban. Todo con coste cero.

## 5. Datos y entrenamiento · 3:00 a 4:00 · B

> Los datos son lo más delicado. Tenemos 23 imágenes reales de pádel y 21 cajas del logo, todas aprobadas por una persona. Una sola clase, nox_texto: 19 imágenes para entrenar, 3 para validar y 1 para probar. Separamos por origen del vídeo para que fotogramas casi idénticos no acaben en entrenamiento y prueba, y guardamos el hash de cada archivo. Hemos hecho cuatro entrenamientos reales. Los controles evitan manipular los resultados: un solo intento, umbral fijado antes de ver los resultados y datos sintéticos fuera de la evaluación.

## 6. Resultados, sin maquillar · 4:00 a 5:00 · B

> Aquí está lo importante. Un diagnóstico demostró que el proceso puede aprender: ajustó una muestra de cuatro imágenes de entrenamiento sin errores. Pero el entrenamiento completo no detectó bien: mAP50 de cero en validación y, en cuatro imágenes revisadas, ningún acierto, un falso positivo y tres logos sin detectar. Por eso decimos que el modelo no está aceptado. Con 23 imágenes y una sola de prueba no podemos afirmar que generalice. Necesitamos más ejemplos de ropa y palas y un test independiente.

## 7. Demo en vivo · 5:00 a 7:30 · A maneja, B comenta

> **A:** Pasamos a la demo, en directo. Abrimos Mozart en local, en el navegador.
>
> **B:** Un aviso recuerda que el modelo es experimental y que la exposición todavía no se calcula.
>
> **A:** Elegimos Desde mi equipo, cargamos un vídeo local de siete segundos e iniciamos el análisis.
>
> **B:** Mientras procesa: no va a la velocidad de reproducción. En los ensayos, siete segundos de vídeo tardaron entre 70 y 79, porque se analiza cada fotograma en CPU. En pantalla se ven los estados del análisis.
>
> **A:** Ya está listo. Leemos las cifras en pantalla: duración, fotogramas y propuestas. Reproducimos el vídeo anotado, sin audio, con las cajas y la clase debajo.
>
> **B:** Cada caja es una propuesta automática, no una aparición confirmada. La confianza no es precisión. Todas aparecen sin revisar.
>
> **A:** Y podemos descargar el vídeo, el CSV de propuestas o el informe JSON.
>
> **B:** El vídeo de la demo comparte un fotograma con el entrenamiento, así que sirve para ver cómo funciona, no para medir calidad.

## 8. Calidad de ingeniería · 7:30 a 8:15 · B

> En ingeniería: 137 pruebas automáticas que pasan en integración continua, 40 commits en ramas cortas con revisión y un Kanban de 14 tareas con decisiones y bloqueos. Esas pruebas verifican el software con detectores simulados, no la calidad del modelo. Datos, vídeos y pesos quedan fuera de Git.

## 9. Niveles del brief · 8:15 a 9:00 · A

> Estado por niveles. Esencial: preparado, faltan el entrenamiento y la evaluación reales. Medio: el vídeo anotado funciona, con modelo experimental. Avanzado: pendiente, con segundos y porcentaje, recortes y segunda marca. Dos variantes de NOX no son dos marcas. Experto: la interfaz web local está lista, falta la API en la nube. Ningún nivel lo damos por completo sin evidencia.

## 10. Siguientes pasos y cierre · 9:00 a 9:45 · B y A

> **B:** Los siguientes pasos son documentar los permisos de reutilización, hacer un nuevo entrenamiento con su evaluación, una sola vez y con test independiente, medir segundos y porcentaje, y ampliar a más marcas, recortes y API en la nube.
>
> **A:** Lo que más nos ha enseñado este proyecto es que la parte difícil es el dato, no el código. Gracias. ¿Alguna pregunta?

## Preguntas

| Quién responde | Temas | Anexo |
| --- | --- | --- |
| A | Brief, arquitectura, uso y opciones de detección | A, C y D |
| B | Datos, resultados, ingeniería y derechos | B y E |

- **Docker o tiempo real:** el brief los recomienda o los menciona, pero no se han incluido ni probado. Decirlo con franqueza.
- **Por qué falla el modelo:** hay pocos datos, y 14 de las 19 imágenes de entrenamiento vienen de solo dos vídeos.
- **Por qué no hay porcentaje:** solo debe medirse con un modelo aceptado, y medir antes sería inventar.

## Antes de empezar

- **Cifras de la demo:** las del análisis en vivo se leen en pantalla. No las des de memoria.
- **Permiso del vídeo:** confírmalo antes. Si no consta, usa otro vídeo autorizado.
- **Si falla la demo:** pasa al anexo B, con la tabla de propuestas y las cifras, y di que es una captura de un análisis real.
- **Si vais cortos de tiempo:** acortad la diapositiva 4 y la 8, que son las más prescindibles.
- **Modelo y vídeo:** el checkpoint es experimental, con hash `b69c4a576d62a464ba9f27f3754e7a6df90ced79afd7e87b93f8dd22fbbfa171`. El vídeo comparte un fotograma con el entrenamiento y no sirve para evaluar.
