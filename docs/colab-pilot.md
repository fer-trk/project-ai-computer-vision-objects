# Primer ensayo gratuito en Colab

[Abrir el cuaderno en Colab](https://colab.research.google.com/github/fer-trk/project-ai-computer-vision-objects/blob/docs/project-specifications/notebooks/nox_colab_pilot.ipynb).

El usuario eligió Colab gratuito el 26/10/2026. El cuaderno contiene siete bloques de código con explicación en español: comprobar GPU, instalar una versión fijada de Ultralytics, cargar/verificar el ZIP, comprobar configuración y visualizar etiquetas, elegir almacenamiento, entrenar tres épocas y descargar resultados. Todavía no se ha ejecutado en Colab.

## Primer uso

1. Abrir el enlace e iniciar sesión en Google si se solicita. Guardar una copia en Drive si se desea conservar el cuaderno y sus salidas.
2. En Entorno de ejecución → Cambiar tipo de entorno de ejecución, elegir GPU disponible en modalidad gratuita. No comprar unidades ni activar planes.
3. Ejecutar **solo el bloque 1**. Debe mostrar la GPU asignada y superar una operación CUDA. Si no hay GPU o falla, conservar el mensaje; no dar por comprobados los recursos.
4. Después, ejecutar el bloque 2 y resolver cualquier incompatibilidad antes de cargar imágenes. Las instalaciones se realizan en Colab, no en el portátil.
5. Antes de los bloques de datos y entrenamiento, registrar las condiciones de uso/permisos pendientes y revisar la licencia. Elegir Colab no resuelve esas decisiones. No cambia automáticamente la licencia del repositorio.

## Paquete local

El ZIP preparado es `data/review/colab-transfer/nox-exploratory-dataset-2026-10-26.zip` (21.667.925 bytes en la generación del 26/10). Contiene 39 archivos: 18 imágenes, 18 etiquetas y tres archivos de configuración/trazabilidad. Se ha verificado su integridad y permanece excluido de Git.

Reconstrucción desde la raíz del repositorio, tras generar el dataset local:

```powershell
.\.venv\Scripts\python.exe scripts/package_nox_colab.py
```

El empaquetador rechaza sobrescribir un ZIP existente, verifica los hashes y usa solo los archivos declarados. No sube nada. El bloque 3 comprueba el hash esperado del manifiesto; al cambiar el dataset será necesario revisar y actualizar ese hash en el cuaderno.

## Validación y límites

Se validó el esquema con nbformat y la sintaxis Python de las siete celdas. Se ejecutó el bloque de carga en un directorio temporal local con la interfaz de subida simulada y el ZIP real: pasaron extracción, hashes, etiquetas, dimensiones, grupos y reescritura de rutas. Un ZIP de prueba con una etiqueta alterada fue rechazado. Esto no ejecuta PyTorch ni sustituye la prueba del cargador de entrenamiento.

Pendientes en Colab: asignación de GPU, operación CUDA real, resolución de dependencias, lectura mediante Ultralytics, inspección visual de las salidas y entrenamiento. El cuaderno publicado no contiene salidas ni afirmaciones de ejecución. Para verificarlo realmente, seguir los bloques 1–7 en orden una vez resueltos los requisitos de los datos, inspeccionar las dos imágenes anotadas y conservar el cuaderno ejecutado junto con el ZIP de resultados. No se ha hecho revisión visual en un visor de Colab.

Ultralytics se fija en 8.4.189, versión consultada al preparar el archivo; PyTorch procede del entorno de Colab. Se registra pip freeze y se ejecuta pip check: las versiones transitivas no están prefijadas ni se ha demostrado compatibilidad en la sesión. Si pip check detecta conflictos, detenerse y resolverlos, sin ignorarlos.

El entrenamiento propuesto usa YOLO11n, 3 épocas, 640 píxeles y lote de 2. No se ha medido su velocidad ni optimizado la resolución para logos pequeños. El conjunto tiene 15 imágenes de entrenamiento y tres de validación, con un único positivo de validación; no permite evaluación final. Un solo detector de clase nox no aprende automáticamente atributos de claridad o soporte.

Drive es opcional (`USE_DRIVE`); con la configuración predeterminada los checkpoints permanecen en almacenamiento temporal hasta descargarlos. Una interrupción puede perderlos. Si se usa Drive, se requiere la autorización habitual de Google. No montar cuentas ni publicar medios o pesos automáticamente.

Fuentes: [entrenamiento Ultralytics](https://docs.ultralytics.com/modes/train/), [límites de Colab](https://research.google.com/colaboratory/faq.html), [licencias de Ultralytics](https://www.ultralytics.com/license). No se contratan servicios de pago ni se declara cumplida T03, T04 o T05 por preparar el cuaderno.
