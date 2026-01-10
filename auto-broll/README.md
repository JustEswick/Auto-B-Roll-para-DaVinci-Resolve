# Auto-B-Roll para DaVinci Resolve

🎬 **Automatización inteligente de B-Roll para editores de video**

Auto-B-Roll analiza el audio de tus videos tipo "talking head", entiende el contexto semántico y busca automáticamente material visual de apoyo para superponer en tu línea de tiempo de DaVinci Resolve.

## ✨ Características

- 🎙️ **Transcripción automática** con OpenAI Whisper
- 📄 **Importación de guion** para mayor precisión
- 🧠 **Análisis semántico** con spaCy NLP
- 🔍 **Búsqueda en múltiples APIs** de stock gratuitas (Pexels, Pixabay, Unsplash)
- 🎬 **Integración nativa** con DaVinci Resolve via Scripting API
- 🖥️ **Interfaz gráfica moderna** con PySide6

## 🚀 Instalación

### Requisitos previos

- Python 3.10 o superior
- DaVinci Resolve 19/20
- FFmpeg instalado en el sistema

### Instalación con uv (recomendado)

```bash
cd auto-broll
uv sync
```

### Instalación con pip

```bash
cd auto-broll
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -e .
```

## 🎯 Uso

```bash
# Activar entorno virtual
.venv\Scripts\activate  # Windows

# Ejecutar aplicación
python -m src.main
```

## 📁 Estructura del Proyecto

```
auto-broll/
├── src/
│   ├── core/           # Orquestación y pipeline
│   ├── transcription/  # Whisper + importador de guion
│   ├── semantic/       # Análisis NLP con spaCy
│   ├── stock/          # APIs de stock (Pexels, Pixabay, Unsplash)
│   ├── davinci/        # Integración con DaVinci Resolve
│   ├── cache/          # Sistema de caché SQLite
│   └── ui/             # Interfaz gráfica PySide6
├── tests/              # Tests unitarios y de integración
├── data/               # Caché y base de datos
├── resources/          # Iconos y fuentes
└── docs/               # Documentación
```

## 🔑 Configuración de APIs

Crea un archivo `.env` en la raíz del proyecto:

```env
PEXELS_API_KEY=tu_api_key_aqui
PIXABAY_API_KEY=tu_api_key_aqui
UNSPLASH_ACCESS_KEY=tu_api_key_aqui
```

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE) para más detalles.
