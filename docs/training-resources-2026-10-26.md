# Comprobación del entorno de entrenamiento — 26/10/2026

Comprobación de hardware y paquetes instalados, sin instalar dependencias ni entrenar. Confirma el inventario inicial del 20/10; todavía no demuestra viabilidad de un entrenamiento ni de un despliegue.

| Recurso | Resultado observado |
|---|---|
| Sistema | Windows 11 Pro |
| CPU | Intel Core i5-8365U, 4 núcleos / 8 hilos |
| RAM física | 8.386.805.760 bytes, aproximadamente 7,81 GiB |
| RAM libre al consultar | 838.560 KiB, aproximadamente 0,80 GiB; valor transitorio |
| Gráficos detectados | Intel UHD Graphics 620 integrada |
| NVIDIA | No detectada en Win32_VideoController; nvidia-smi no disponible |
| Espacio libre C: | Aproximadamente 101 GiB en la consulta |
| Python del proyecto | 3.11.9, 64 bits |
| Paquetes de preparación | Pillow 13.0.0 y NumPy 2.4.6 instalados |
| Paquetes de entrenamiento | torch, torchvision y ultralytics no instalados en el entorno del proyecto |

Método: consultas Win32_Processor, Win32_ComputerSystem, Win32_OperatingSystem y Win32_VideoController mediante Get-CimInstance; Get-PSDrive; detección de nvidia-smi; versión de Python e importlib.metadata. No se incluyen identificadores personales del equipo. AdapterRAM no se interpreta como memoria dedicada utilizable de entrenamiento en esta GPU integrada.

## Recomendación

Mantener preparación de datos y pruebas pequeñas locales. Para este ensayo, continuar con la opción propuesta previamente de Colab gratuito y el candidato YOLO11n, sin cambiar modelo ni adoptar servicios de pago. Es una recomendación por recursos observados, no una medición de velocidad: no se ha ejecutado un benchmark por CPU. La poca RAM libre desaconseja iniciar ahora una instalación y entrenamiento pesados en el mismo equipo.

[PyTorch permite instalaciones para CPU y CUDA](https://pytorch.org/get-started/locally/); esta GPU Intel no proporciona el camino CUDA de NVIDIA. No se ha evaluado aceleración alternativa de Intel. El soporte de [YOLO11](https://docs.ultralytics.com/models/yolo11/) sigue documentado; no se cambia de familia porque exista una versión posterior.

[Colab ofrece recursos gratuitos sujetos a límites y disponibilidad](https://research.google.com/colaboratory/faq.html). No hay GPU garantizada ni sesión ya asignada. Colab se utilizaría para computación interactiva, no como hosting de la API. La instalación en la sesión cloud y la descarga de pesos no resolverán automáticamente las dependencias del entorno local.

## Siguiente paso verificable

Preparar un cuaderno de Colab que primero compruebe Python, RAM y GPU asignada, registre versiones y pruebe la ejecución de PyTorch. Comprobar la sesión real antes de fijar resolución y tamaño del lote. Una vez revisadas las condiciones de uso/licencias y permisos de los datos, probar la carga de las 18 imágenes y sus etiquetas, y después ejecutar un entrenamiento corto. Si no hay GPU gratuita, registrar el resultado y medir una alternativa mínima por CPU antes de comprometer tiempos.

Pendientes: acceso real a Colab, dependencias instaladas y compatibles, carga Ultralytics del dataset, licencia del modelo y biblioteca, permisos de medios, entrenamiento medido, guardado recuperable de checkpoints, e inferencia mínima en un hosting gratuito. Los tiempos de entrenamiento siguen sin medirse. T03 no se da por completada; T04 sigue como única tarea en curso.
