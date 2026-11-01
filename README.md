# project-ai-computer-vision-objects

## Preparación local para desarrollo

Esta guía prepara el entorno para ejecutar las herramientas y las pruebas
actuales del repositorio en Windows usando Git Bash y Python 3.11.

### Requisitos

- Git Bash.
- Python 3.11 disponible mediante el lanzador `py`.

### Instalación

Clona el repositorio y entra en su carpeta:

```bash
git clone https://github.com/fer-trk/project-ai-computer-vision-objects.git
cd project-ai-computer-vision-objects
```

Comprueba Python, crea el entorno virtual, actívalo y actualiza `pip`:

```bash
py -3.11 --version
py -3.11 -m venv .venv
source .venv/Scripts/activate
python --version
python -m pip install --upgrade pip
```

Instala las dependencias fijadas para las herramientas y las pruebas locales:

```bash
python -m pip install -r requirements-tools.txt
```

Ejecuta las pruebas existentes:

```bash
python -m unittest discover -s tests -v
```

Cuando termines, desactiva el entorno virtual:

```bash
deactivate
```

### Alcance de las dependencias

`requirements-tools.txt` contiene las dependencias del desarrollo local. Incluye
`Pillow` para leer y validar imágenes, `opencv-python-headless` y `numpy` para
las herramientas de inspección de vídeo, y `yt-dlp` junto con sus dependencias
para las utilidades de adquisición y revisión de vídeos. El módulo
`unittest` pertenece a la biblioteca estándar de Python.

Este entorno no instala las dependencias de entrenamiento usadas por el piloto
de Colab. El notebook mantiene su instalación separada y no forma parte de la
validación de estas pruebas.
