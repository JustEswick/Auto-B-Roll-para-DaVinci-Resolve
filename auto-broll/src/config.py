"""
Configuración global de Auto-B-Roll.

Este módulo maneja la configuración de la aplicación, incluyendo
rutas, API keys, y preferencias del usuario.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import json

from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


# =============================================================================
# RUTAS DEL PROYECTO
# =============================================================================

# Directorio raíz del proyecto
PROJECT_ROOT = Path(__file__).parent.parent

# Directorios de datos
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
DB_DIR = DATA_DIR / "db"

# Directorios de recursos
RESOURCES_DIR = PROJECT_ROOT / "resources"
ICONS_DIR = RESOURCES_DIR / "icons"
FONTS_DIR = RESOURCES_DIR / "fonts"

# Archivo de configuración del usuario
USER_CONFIG_FILE = DATA_DIR / "config.json"

# Base de datos SQLite
DATABASE_PATH = DB_DIR / "auto_broll.db"


# =============================================================================
# API KEYS
# =============================================================================

@dataclass
class APIKeys:
    """Contenedor para API keys de servicios externos."""
    
    pexels: Optional[str] = field(default_factory=lambda: os.getenv("PEXELS_API_KEY"))
    pixabay: Optional[str] = field(default_factory=lambda: os.getenv("PIXABAY_API_KEY"))
    unsplash: Optional[str] = field(default_factory=lambda: os.getenv("UNSPLASH_ACCESS_KEY"))
    openai: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    
    def is_pexels_configured(self) -> bool:
        return bool(self.pexels)
    
    def is_pixabay_configured(self) -> bool:
        return bool(self.pixabay)
    
    def is_unsplash_configured(self) -> bool:
        return bool(self.unsplash)
    
    def get_available_apis(self) -> list[str]:
        """Retorna lista de APIs configuradas."""
        apis = []
        if self.is_pexels_configured():
            apis.append("pexels")
        if self.is_pixabay_configured():
            apis.append("pixabay")
        if self.is_unsplash_configured():
            apis.append("unsplash")
        return apis


# =============================================================================
# CONFIGURACIÓN DE WHISPER
# =============================================================================

@dataclass
class WhisperConfig:
    """Configuración para OpenAI Whisper."""
    
    model: str = "base"  # tiny, base, small, medium, large
    language: Optional[str] = "es"  # None para auto-detect
    task: str = "transcribe"
    word_timestamps: bool = True
    fp16: bool = True  # GPU acceleration
    
    @property
    def available_models(self) -> list[str]:
        return ["tiny", "base", "small", "medium", "large"]


# =============================================================================
# CONFIGURACIÓN DE BÚSQUEDA DE ASSETS
# =============================================================================

@dataclass
class SearchConfig:
    """Configuración para búsqueda de assets."""
    
    results_per_api: int = 10
    preferred_orientation: str = "landscape"  # landscape, portrait, square
    preferred_type: str = "video"  # video, image, all
    min_width: int = 1280
    min_height: int = 720


# =============================================================================
# CONFIGURACIÓN DE TIMELINE
# =============================================================================

@dataclass
class TimelineConfig:
    """Configuración para inserción en timeline."""
    
    default_clip_duration: float = 3.0  # segundos
    target_track: int = 2  # Track de video para B-Roll
    fade_duration: float = 0.5  # segundos de fade in/out
    auto_insert: bool = False  # Requiere aprobación por defecto


# =============================================================================
# CONFIGURACIÓN PRINCIPAL
# =============================================================================

@dataclass
class AppConfig:
    """Configuración principal de la aplicación."""
    
    api_keys: APIKeys = field(default_factory=APIKeys)
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    timeline: TimelineConfig = field(default_factory=TimelineConfig)
    
    # UI
    theme: str = "dark"  # dark, light
    language: str = "es"  # es, en
    
    def save(self, path: Optional[Path] = None) -> None:
        """Guarda la configuración en archivo JSON."""
        config_path = path or USER_CONFIG_FILE
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        config_dict = {
            "whisper": {
                "model": self.whisper.model,
                "language": self.whisper.language,
            },
            "search": {
                "results_per_api": self.search.results_per_api,
                "preferred_orientation": self.search.preferred_orientation,
                "preferred_type": self.search.preferred_type,
            },
            "timeline": {
                "default_clip_duration": self.timeline.default_clip_duration,
                "target_track": self.timeline.target_track,
                "fade_duration": self.timeline.fade_duration,
                "auto_insert": self.timeline.auto_insert,
            },
            "theme": self.theme,
            "language": self.language,
        }
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load(cls, path: Optional[Path] = None) -> "AppConfig":
        """Carga la configuración desde archivo JSON."""
        config_path = path or USER_CONFIG_FILE
        
        if not config_path.exists():
            return cls()
        
        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = json.load(f)
        
        config = cls()
        
        if "whisper" in config_dict:
            config.whisper.model = config_dict["whisper"].get("model", "base")
            config.whisper.language = config_dict["whisper"].get("language", "es")
        
        if "search" in config_dict:
            config.search.results_per_api = config_dict["search"].get("results_per_api", 10)
            config.search.preferred_orientation = config_dict["search"].get("preferred_orientation", "landscape")
            config.search.preferred_type = config_dict["search"].get("preferred_type", "video")
        
        if "timeline" in config_dict:
            config.timeline.default_clip_duration = config_dict["timeline"].get("default_clip_duration", 3.0)
            config.timeline.target_track = config_dict["timeline"].get("target_track", 2)
            config.timeline.fade_duration = config_dict["timeline"].get("fade_duration", 0.5)
            config.timeline.auto_insert = config_dict["timeline"].get("auto_insert", False)
        
        config.theme = config_dict.get("theme", "dark")
        config.language = config_dict.get("language", "es")
        
        return config


# Instancia global de configuración
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Obtiene la configuración global de la aplicación."""
    global _config
    if _config is None:
        _config = AppConfig.load()
    return _config


def save_config() -> None:
    """Guarda la configuración global."""
    global _config
    if _config is not None:
        _config.save()


# =============================================================================
# INICIALIZACIÓN DE DIRECTORIOS
# =============================================================================

def init_directories() -> None:
    """Crea los directorios necesarios si no existen."""
    directories = [
        DATA_DIR,
        CACHE_DIR,
        DB_DIR,
        RESOURCES_DIR,
        ICONS_DIR,
        FONTS_DIR,
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
