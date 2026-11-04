# Comprobar Colab antes de T05

Estado: preparación validada en local mediante simulación, sin sesión real de Colab ni GPU utilizada. Este control no entrena, no descarga pesos y no demuestra calidad del detector.

## Una sola sesión para el flujo de entrenamiento

La ruta recomendada es abrir directamente [nox_text_training.ipynb](../notebooks/nox_text_training.ipynb) y ejecutar sus dos primeras celdas antes de subir datos:

1. Seleccionar GPU gratuita. La primera celda comprueba CUDA con una operación pequeña.
2. La segunda exige esa comprobación previa y que CUDA siga disponible antes de instalar. Fija Ultralytics 8.4.189, instala Jedi si falta, ejecuta `pip check`, desactiva integraciones opcionales y vuelve a comprobar versión y disponibilidad de GPU.
3. Solo si ambas pasan, continuar **en ese mismo cuaderno y entorno**, con permisos documentados, ZIP aprobado y el umbral elegido antes de entrenar. La subida del dataset, configuración del run y entrenamiento se detienen si el entorno no quedó preparado o perdió la GPU.

No se reinicia automáticamente ni se repite el entrenamiento por un fallo de instalación. Sin GPU o si se pide reiniciar, detenerse y revisar el entorno antes de entrenar. No comprar unidades ni activar servicios de pago.

Las comprobaciones no crean los bloqueos de entrenamiento. Los bloqueos y el ensayo único siguen rigiéndose por [T05](t05-one-run.md).

## Cuaderno independiente

[nox_colab_env_check.ipynb](../notebooks/nox_colab_env_check.ipynb) permite diagnosticar un entorno sin introducir el dataset. Ejecutar sus tres celdas en orden.

Su resultado solo vale para el entorno donde se ejecutó. Abrir otro notebook no garantiza compartir la GPU ni los paquetes. No usar el éxito de este diagnóstico como permiso para saltar las comprobaciones del cuaderno de T05.

No solicita archivos, no monta Drive, no usa datos sintéticos o reales, no ejecuta entrenamiento/evaluación/predicción y no descarga modelos. Instalar dependencias puede modificar paquetes y los ajustes de Ultralytics; repetir la comprobación no es repetir el entrenamiento.

## Comprobaciones locales

Las pruebas reemplazan CUDA, las instalaciones y Ultralytics por controles temporales; no ejecutan `pip` ni crean un modelo. Cubren falta de GPU, operación GPU fallida, salto de la primera celda, pérdida de GPU, fallo de dependencias, versión incorrecta y resumen después de un error. También prueban que un entorno fallido bloquea la subida, configuración y entrenamiento de T05.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_colab_env_check.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_nox_text_one_run.py -v
```

La disponibilidad real de Colab, su instalación y el entrenamiento permanecen pendientes; las simulaciones no los sustituyen. El cuaderno conserva las salidas vacías.

### Validación — 04/11/2026

- **89 pruebas de la rama correctas, sin omisiones**, incluidas 12 del control de entorno y las pruebas de T05 ya integrado.
- Ambos cuadernos tienen sintaxis válida y salidas vacías. El cuaderno de entrenamiento coincide exactamente con su generador y los enlaces relativos de las guías existen.
- Los parámetros de entrenamiento y la selección explícita de umbral permanecen sin cambios. No se ejecutó entrenamiento ni se usó GPU.
