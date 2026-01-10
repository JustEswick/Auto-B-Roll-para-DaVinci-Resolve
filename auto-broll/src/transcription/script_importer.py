"""
Importador de Guiones.

Este módulo permite importar guiones en diferentes formatos
(TXT, SRT, DOCX, MD) para mejorar la precisión de la transcripción.
"""

from typing import Optional, List, Tuple
from pathlib import Path
from dataclasses import dataclass
import re
import logging

logger = logging.getLogger(__name__)


class ScriptImportError(Exception):
    """Error durante la importación de guion."""
    pass


@dataclass
class ScriptLine:
    """Representa una línea del guion."""
    text: str
    start_time: Optional[float] = None  # Segundos
    end_time: Optional[float] = None
    line_number: int = 0


@dataclass
class ImportedScript:
    """Guion importado con su contenido parseado."""
    source_file: str
    format: str  # txt, srt, docx, md
    lines: List[ScriptLine]
    full_text: str = ""
    has_timestamps: bool = False
    
    @property
    def word_count(self) -> int:
        return len(self.full_text.split())
    
    @property
    def line_count(self) -> int:
        return len(self.lines)


class ScriptImporter:
    """
    Importador de guiones de video.
    
    Soporta múltiples formatos y extrae el texto junto con
    timestamps cuando están disponibles.
    """
    
    SUPPORTED_FORMATS = {
        ".txt": "text",
        ".srt": "srt",
        ".md": "markdown",
        ".docx": "docx",
    }
    
    def __init__(self):
        self._last_import: Optional[ImportedScript] = None
    
    def is_supported(self, file_path: Path) -> bool:
        """Verifica si el formato es soportado."""
        return file_path.suffix.lower() in self.SUPPORTED_FORMATS
    
    def load(self, file_path: Path) -> ImportedScript:
        """
        Carga un archivo de guion.
        
        Args:
            file_path: Ruta al archivo
            
        Returns:
            Script importado
            
        Raises:
            ScriptImportError: Si el archivo no puede ser leído
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise ScriptImportError(f"El archivo no existe: {file_path}")
        
        suffix = file_path.suffix.lower()
        
        if suffix not in self.SUPPORTED_FORMATS:
            raise ScriptImportError(
                f"Formato no soportado: {suffix}\n"
                f"Formatos válidos: {list(self.SUPPORTED_FORMATS.keys())}"
            )
        
        format_type = self.SUPPORTED_FORMATS[suffix]
        
        logger.info(f"Importando guion: {file_path.name} (formato: {format_type})")
        
        try:
            if format_type == "srt":
                script = self._load_srt(file_path)
            elif format_type == "docx":
                script = self._load_docx(file_path)
            else:  # txt, markdown
                script = self._load_text(file_path)
            
            self._last_import = script
            
            logger.info(
                f"Guion importado: {script.line_count} líneas, "
                f"{script.word_count} palabras"
            )
            
            return script
            
        except Exception as e:
            raise ScriptImportError(f"Error al leer el archivo: {e}")
    
    def _load_text(self, file_path: Path) -> ImportedScript:
        """Carga un archivo de texto plano o markdown."""
        content = file_path.read_text(encoding="utf-8")
        
        # Para markdown, eliminar sintaxis básica
        if file_path.suffix.lower() == ".md":
            content = self._clean_markdown(content)
        
        lines = []
        for i, line_text in enumerate(content.splitlines(), 1):
            line_text = line_text.strip()
            if line_text:  # Ignorar líneas vacías
                lines.append(ScriptLine(
                    text=line_text,
                    line_number=i
                ))
        
        full_text = " ".join(line.text for line in lines)
        
        return ImportedScript(
            source_file=str(file_path),
            format=file_path.suffix.lower().lstrip("."),
            lines=lines,
            full_text=full_text,
            has_timestamps=False,
        )
    
    def _load_srt(self, file_path: Path) -> ImportedScript:
        """Carga un archivo SRT con timestamps."""
        content = file_path.read_text(encoding="utf-8")
        
        # Patrón para parsear SRT
        # Formato: índice, timestamp --> timestamp, texto
        pattern = re.compile(
            r'(\d+)\s*\n'
            r'(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*\n'
            r'((?:(?!\n\n|\n\d+\s*\n).)+)',
            re.MULTILINE | re.DOTALL
        )
        
        lines = []
        for match in pattern.finditer(content):
            index = int(match.group(1))
            start_str = match.group(2)
            end_str = match.group(3)
            text = match.group(4).strip().replace('\n', ' ')
            
            start_time = self._parse_srt_time(start_str)
            end_time = self._parse_srt_time(end_str)
            
            lines.append(ScriptLine(
                text=text,
                start_time=start_time,
                end_time=end_time,
                line_number=index,
            ))
        
        full_text = " ".join(line.text for line in lines)
        
        return ImportedScript(
            source_file=str(file_path),
            format="srt",
            lines=lines,
            full_text=full_text,
            has_timestamps=True,
        )
    
    def _load_docx(self, file_path: Path) -> ImportedScript:
        """Carga un archivo DOCX."""
        try:
            from docx import Document
        except ImportError:
            raise ScriptImportError(
                "python-docx no está instalado.\n"
                "Instálalo con: pip install python-docx"
            )
        
        doc = Document(file_path)
        
        lines = []
        line_num = 1
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                lines.append(ScriptLine(
                    text=text,
                    line_number=line_num,
                ))
                line_num += 1
        
        full_text = " ".join(line.text for line in lines)
        
        return ImportedScript(
            source_file=str(file_path),
            format="docx",
            lines=lines,
            full_text=full_text,
            has_timestamps=False,
        )
    
    def _parse_srt_time(self, time_str: str) -> float:
        """
        Parsea un timestamp SRT a segundos.
        
        Args:
            time_str: Timestamp en formato HH:MM:SS,mmm
            
        Returns:
            Tiempo en segundos
        """
        # Normalizar separador de milisegundos
        time_str = time_str.replace(',', '.')
        
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        
        return hours * 3600 + minutes * 60 + seconds
    
    def _clean_markdown(self, content: str) -> str:
        """
        Limpia sintaxis markdown básica.
        
        Args:
            content: Contenido markdown
            
        Returns:
            Texto limpio
        """
        # Eliminar headers
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
        
        # Eliminar bold/italic
        content = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', content)
        content = re.sub(r'_{1,2}([^_]+)_{1,2}', r'\1', content)
        
        # Eliminar links
        content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)
        
        # Eliminar código inline
        content = re.sub(r'`([^`]+)`', r'\1', content)
        
        # Eliminar bloques de código
        content = re.sub(r'```[\s\S]*?```', '', content)
        
        # Eliminar listas
        content = re.sub(r'^[\s]*[-*+]\s+', '', content, flags=re.MULTILINE)
        content = re.sub(r'^[\s]*\d+\.\s+', '', content, flags=re.MULTILINE)
        
        return content.strip()
    
    @property
    def last_import(self) -> Optional[ImportedScript]:
        """Retorna el último script importado."""
        return self._last_import
