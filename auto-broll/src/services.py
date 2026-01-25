"""
Servicios de la Aplicación.

Este módulo proporciona servicios de alto nivel que conectan
la GUI con los módulos backend, ejecutando operaciones en
hilos separados para no bloquear la UI.
"""

from typing import Optional, List, Callable, Any
from pathlib import Path
from dataclasses import dataclass
import asyncio
import logging

from PySide6.QtCore import QObject, Signal, QThread, QRunnable, QThreadPool

logger = logging.getLogger(__name__)


# =============================================================================
# Workers para operaciones en background
# =============================================================================

class TranscriptionWorker(QThread):
    """Worker para transcripción en background."""
    
    progress = Signal(float, str)  # (progress 0-1, message)
    finished = Signal(object)  # Transcription result
    error = Signal(str)
    
    def __init__(
        self,
        video_path: Path,
        model: str = "base",
        language: Optional[str] = "es",
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self.video_path = video_path
        self.model = model
        self.language = language
        self._cancelled = False
    
    def run(self):
        try:
            from src.core.audio_extractor import AudioExtractor
            from src.transcription.whisper_service import WhisperService
            
            # Paso 1: Extraer audio
            self.progress.emit(0.1, "Extrayendo audio del video...")
            
            extractor = AudioExtractor()
            audio_path = extractor.extract(self.video_path)
            
            if self._cancelled:
                return
            
            # Paso 2: Transcribir
            self.progress.emit(0.3, f"Transcribiendo con Whisper ({self.model})...")
            
            whisper = WhisperService(model_name=self.model)
            
            def progress_callback(p: float):
                self.progress.emit(0.3 + p * 0.6, "Transcribiendo...")
            
            transcription = whisper.transcribe(
                audio_path,
                language=self.language,
                progress_callback=progress_callback
            )
            
            if self._cancelled:
                return
            
            self.progress.emit(1.0, "Transcripción completada")
            self.finished.emit(transcription)
            
        except Exception as e:
            logger.error(f"Error en transcripción: {e}")
            self.error.emit(str(e))
    
    def cancel(self):
        self._cancelled = True


class AnalysisWorker(QThread):
    """Worker para análisis semántico en background."""
    
    progress = Signal(float, str)
    finished = Signal(object)  # AnalysisResult
    error = Signal(str)
    
    def __init__(
        self,
        text: str,
        timestamps: Optional[List] = None,
        language: str = "es",
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self.text = text
        self.timestamps = timestamps
        self.language = language
    
    def run(self):
        try:
            from src.semantic.analyzer import SemanticAnalyzer
            
            self.progress.emit(0.2, "Cargando modelo NLP...")
            
            analyzer = SemanticAnalyzer(language=self.language)
            
            self.progress.emit(0.5, "Analizando conceptos visualizables...")
            
            result = analyzer.analyze(self.text, self.timestamps)
            
            self.progress.emit(1.0, f"Encontrados {len(result.concepts)} conceptos")
            self.finished.emit(result)
            
        except Exception as e:
            logger.error(f"Error en análisis: {e}")
            self.error.emit(str(e))


class SearchWorker(QThread):
    """Worker para búsqueda de assets en background."""
    
    progress = Signal(float, str)
    finished = Signal(dict)  # {keyword: [StockAsset]}
    error = Signal(str)
    
    def __init__(
        self,
        keywords: List[str],
        asset_type: Optional[str] = None,
        per_keyword: int = 5,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self.keywords = keywords
        self.asset_type = asset_type
        self.per_keyword = per_keyword
    
    def run(self):
        try:
            import sys
            import asyncio
            
            # En Windows, usar SelectorEventLoop para evitar problemas con httpx
            if sys.platform == 'win32':
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            
            # Ejecutar búsqueda async
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(self._search())
                self.finished.emit(result)
            finally:
                # Cerrar pendientes y luego el loop
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
                
        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")
            self.error.emit(str(e))
    
    async def _search(self):
        from src.stock.aggregator import StockAggregator
        from src.stock.base import AssetType
        
        self.progress.emit(0.1, "Inicializando búsqueda...")
        
        aggregator = StockAggregator()
        
        if not aggregator.is_any_configured():
            raise RuntimeError(
                "No hay APIs de stock configuradas.\n"
                "Configura al menos una API key en Configuración."
            )
        
        asset_type = None
        if self.asset_type == "video":
            asset_type = AssetType.VIDEO
        elif self.asset_type == "image":
            asset_type = AssetType.IMAGE
        
        total = len(self.keywords)
        results = {}
        
        for i, keyword in enumerate(self.keywords):
            self.progress.emit(
                (i + 1) / total,
                f"Buscando '{keyword}'... ({i + 1}/{total})"
            )
            
            assets = await aggregator.search(
                keyword,
                asset_type=asset_type,
                per_api=self.per_keyword
            )
            results[keyword] = assets
        
        await aggregator.close()
        
        self.progress.emit(1.0, "Búsqueda completada")
        return results


class DownloadWorker(QThread):
    """Worker para descarga de assets en background."""
    
    progress = Signal(int, int, str)  # (completed, total, current_file)
    finished = Signal(list)  # Lista de paths descargados
    error = Signal(str)
    
    def __init__(
        self,
        assets: List,
        download_dir: Path,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self.assets = assets
        self.download_dir = download_dir
    
    def run(self):
        try:
            import sys
            
            # En Windows, usar SelectorEventLoop para evitar problemas con httpx
            if sys.platform == 'win32':
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(self._download())
                self.finished.emit(result)
            finally:
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
                
        except Exception as e:
            logger.error(f"Error en descarga: {e}")
            self.error.emit(str(e))
    
    async def _download(self):
        from src.stock.downloader import AssetDownloader
        
        downloader = AssetDownloader(self.download_dir)
        
        def progress_callback(completed: int, total: int):
            current = self.assets[completed - 1].id if completed > 0 else ""
            self.progress.emit(completed, total, current)
        
        results = await downloader.download_many(
            self.assets,
            progress_callback=progress_callback
        )
        
        # Retornar solo los paths exitosos
        return [r.local_path for r in results if r.success and r.local_path]


# =============================================================================
# Servicio Principal
# =============================================================================

class AppServices(QObject):
    """
    Servicios centrales de la aplicación.
    
    Proporciona métodos para ejecutar operaciones de backend
    desde la GUI de forma asíncrona.
    """
    
    # Señales de estado
    transcription_started = Signal()
    transcription_progress = Signal(float, str)
    transcription_finished = Signal(object)
    transcription_error = Signal(str)
    
    analysis_started = Signal()
    analysis_finished = Signal(object)
    analysis_error = Signal(str)
    
    search_started = Signal()
    search_progress = Signal(float, str)
    search_finished = Signal(dict)
    search_error = Signal(str)
    
    download_started = Signal()
    download_progress = Signal(int, int, str)
    download_finished = Signal(list)
    download_error = Signal(str)
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        self._transcription_worker: Optional[TranscriptionWorker] = None
        self._analysis_worker: Optional[AnalysisWorker] = None
        self._search_worker: Optional[SearchWorker] = None
        self._download_worker: Optional[DownloadWorker] = None
        
        # Estado actual
        self._current_transcription = None
        self._current_analysis = None
        self._current_assets = {}
    
    # =========================================================================
    # Transcripción
    # =========================================================================
    
    def start_transcription(
        self,
        video_path: Path,
        model: str = "base",
        language: Optional[str] = "es"
    ) -> None:
        """Inicia la transcripción de un video."""
        if self._transcription_worker and self._transcription_worker.isRunning():
            logger.warning("Ya hay una transcripción en curso")
            return
        
        self._transcription_worker = TranscriptionWorker(
            video_path, model, language
        )
        self._transcription_worker.progress.connect(self.transcription_progress.emit)
        self._transcription_worker.finished.connect(self._on_transcription_finished)
        self._transcription_worker.error.connect(self.transcription_error.emit)
        
        self.transcription_started.emit()
        self._transcription_worker.start()
    
    def _on_transcription_finished(self, result):
        self._current_transcription = result
        self.transcription_finished.emit(result)
    
    def cancel_transcription(self) -> None:
        """Cancela la transcripción en curso."""
        if self._transcription_worker:
            self._transcription_worker.cancel()
    
    # =========================================================================
    # Análisis Semántico
    # =========================================================================
    
    def start_analysis(
        self,
        text: str,
        timestamps: Optional[List] = None,
        language: str = "es"
    ) -> None:
        """Inicia el análisis semántico del texto."""
        if self._analysis_worker and self._analysis_worker.isRunning():
            logger.warning("Ya hay un análisis en curso")
            return
        
        self._analysis_worker = AnalysisWorker(text, timestamps, language)
        self._analysis_worker.progress.connect(lambda p, m: None)  # Silencioso
        self._analysis_worker.finished.connect(self._on_analysis_finished)
        self._analysis_worker.error.connect(self.analysis_error.emit)
        
        self.analysis_started.emit()
        self._analysis_worker.start()
    
    def _on_analysis_finished(self, result):
        self._current_analysis = result
        self.analysis_finished.emit(result)
    
    # =========================================================================
    # Búsqueda de Assets
    # =========================================================================
    
    def start_search(
        self,
        keywords: List[str],
        asset_type: Optional[str] = None,
        per_keyword: int = 5
    ) -> None:
        """Inicia la búsqueda de assets."""
        if self._search_worker and self._search_worker.isRunning():
            logger.warning("Ya hay una búsqueda en curso")
            return
        
        self._search_worker = SearchWorker(keywords, asset_type, per_keyword)
        self._search_worker.progress.connect(self.search_progress.emit)
        self._search_worker.finished.connect(self._on_search_finished)
        self._search_worker.error.connect(self.search_error.emit)
        
        self.search_started.emit()
        self._search_worker.start()
    
    def _on_search_finished(self, result):
        self._current_assets = result
        self.search_finished.emit(result)
    
    # =========================================================================
    # Descarga
    # =========================================================================
    
    def start_download(
        self,
        assets: List,
        download_dir: Optional[Path] = None
    ) -> None:
        """Inicia la descarga de assets."""
        if self._download_worker and self._download_worker.isRunning():
            logger.warning("Ya hay una descarga en curso")
            return
        
        if download_dir is None:
            from src.config import CACHE_DIR
            download_dir = CACHE_DIR / "downloads"
        
        download_dir.mkdir(parents=True, exist_ok=True)
        
        self._download_worker = DownloadWorker(assets, download_dir)
        self._download_worker.progress.connect(self.download_progress.emit)
        self._download_worker.finished.connect(self.download_finished.emit)
        self._download_worker.error.connect(self.download_error.emit)
        
        self.download_started.emit()
        self._download_worker.start()
    
    # =========================================================================
    # Propiedades
    # =========================================================================
    
    @property
    def current_transcription(self):
        """Retorna la transcripción actual."""
        return self._current_transcription
    
    @property
    def current_analysis(self):
        """Retorna el análisis actual."""
        return self._current_analysis
    
    @property
    def current_assets(self) -> dict:
        """Retorna los assets encontrados."""
        return self._current_assets


# Instancia global de servicios
_services: Optional[AppServices] = None


def get_services() -> AppServices:
    """Obtiene la instancia global de servicios."""
    global _services
    if _services is None:
        _services = AppServices()
    return _services
