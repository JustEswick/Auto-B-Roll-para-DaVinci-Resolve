"""
Base de Datos SQLite.

Este módulo maneja el almacenamiento persistente de datos
como assets descargados, configuración y caché de búsquedas.
"""

from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import sqlite3
import json
import logging

logger = logging.getLogger(__name__)


class Database:
    """
    Gestor de base de datos SQLite para Auto-B-Roll.
    
    Almacena:
    - Assets descargados y su metadata
    - Historial de búsquedas
    - Caché de resultados de APIs
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Inicializa la base de datos.
        
        Args:
            db_path: Ruta al archivo de base de datos
        """
        if db_path is None:
            from ..config import DATABASE_PATH
            db_path = DATABASE_PATH
        
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._connection: Optional[sqlite3.Connection] = None
        self._init_db()
    
    def _init_db(self) -> None:
        """Inicializa las tablas de la base de datos."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Tabla de assets descargados
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assets (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                type TEXT NOT NULL,
                preview_url TEXT,
                download_url TEXT,
                page_url TEXT,
                local_path TEXT,
                thumbnail_path TEXT,
                width INTEGER,
                height INTEGER,
                duration REAL,
                search_query TEXT,
                downloaded_at TIMESTAMP,
                last_used_at TIMESTAMP,
                use_count INTEGER DEFAULT 0,
                metadata TEXT
            )
        """)
        
        # Tabla de historial de búsquedas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                source TEXT,
                result_count INTEGER,
                searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla de caché de búsquedas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_cache (
                query TEXT NOT NULL,
                source TEXT NOT NULL,
                results TEXT,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                PRIMARY KEY (query, source)
            )
        """)
        
        # Tabla de keywords y conceptos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT UNIQUE NOT NULL,
                translation TEXT,
                category TEXT,
                search_count INTEGER DEFAULT 0,
                last_searched_at TIMESTAMP
            )
        """)
        
        # Índices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_assets_source ON assets(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_assets_query ON assets(search_query)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_cache_query ON search_cache(query)")
        
        conn.commit()
        logger.info(f"Base de datos inicializada: {self._db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Obtiene la conexión a la base de datos."""
        if self._connection is None:
            self._connection = sqlite3.connect(
                str(self._db_path),
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            self._connection.row_factory = sqlite3.Row
        return self._connection
    
    def close(self) -> None:
        """Cierra la conexión a la base de datos."""
        if self._connection:
            self._connection.close()
            self._connection = None
    
    # =========================================================================
    # Assets
    # =========================================================================
    
    def save_asset(self, asset_data: Dict[str, Any]) -> bool:
        """
        Guarda o actualiza un asset.
        
        Args:
            asset_data: Diccionario con datos del asset
            
        Returns:
            True si fue exitoso
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO assets (
                    id, source, type, preview_url, download_url, page_url,
                    local_path, thumbnail_path, width, height, duration,
                    search_query, downloaded_at, last_used_at, use_count, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                asset_data.get("id"),
                asset_data.get("source"),
                asset_data.get("type"),
                asset_data.get("preview_url"),
                asset_data.get("download_url"),
                asset_data.get("page_url"),
                asset_data.get("local_path"),
                asset_data.get("thumbnail_path"),
                asset_data.get("width"),
                asset_data.get("height"),
                asset_data.get("duration"),
                asset_data.get("search_query"),
                asset_data.get("downloaded_at", datetime.now()),
                asset_data.get("last_used_at"),
                asset_data.get("use_count", 0),
                json.dumps(asset_data.get("metadata", {})),
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error guardando asset: {e}")
            return False
    
    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene un asset por ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM assets WHERE id = ?", (asset_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def get_assets_by_query(self, query: str) -> List[Dict[str, Any]]:
        """Obtiene assets por query de búsqueda."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM assets WHERE search_query LIKE ? ORDER BY use_count DESC",
            (f"%{query}%",)
        )
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_downloaded_assets(self) -> List[Dict[str, Any]]:
        """Obtiene todos los assets descargados."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM assets WHERE local_path IS NOT NULL ORDER BY downloaded_at DESC"
        )
        
        return [dict(row) for row in cursor.fetchall()]
    
    def increment_asset_usage(self, asset_id: str) -> None:
        """Incrementa el contador de uso de un asset."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE assets 
            SET use_count = use_count + 1, last_used_at = ? 
            WHERE id = ?
        """, (datetime.now(), asset_id))
        
        conn.commit()
    
    def delete_asset(self, asset_id: str) -> bool:
        """Elimina un asset."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
        conn.commit()
        
        return cursor.rowcount > 0
    
    # =========================================================================
    # Búsquedas
    # =========================================================================
    
    def add_search_history(self, query: str, source: str, result_count: int) -> None:
        """Agrega una búsqueda al historial."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO search_history (query, source, result_count)
            VALUES (?, ?, ?)
        """, (query, source, result_count))
        
        conn.commit()
    
    def get_search_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtiene el historial de búsquedas."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM search_history 
            ORDER BY searched_at DESC 
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_popular_queries(self, limit: int = 10) -> List[str]:
        """Obtiene las búsquedas más populares."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT query, COUNT(*) as count 
            FROM search_history 
            GROUP BY query 
            ORDER BY count DESC 
            LIMIT ?
        """, (limit,))
        
        return [row["query"] for row in cursor.fetchall()]
    
    # =========================================================================
    # Caché
    # =========================================================================
    
    def cache_search_results(
        self,
        query: str,
        source: str,
        results: List[Dict],
        ttl_hours: int = 24
    ) -> None:
        """
        Cachea resultados de búsqueda.
        
        Args:
            query: Query de búsqueda
            source: Fuente (pexels, pixabay, etc.)
            results: Lista de resultados
            ttl_hours: Tiempo de vida en horas
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        from datetime import timedelta
        expires_at = datetime.now() + timedelta(hours=ttl_hours)
        
        cursor.execute("""
            INSERT OR REPLACE INTO search_cache (query, source, results, cached_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, (query, source, json.dumps(results), datetime.now(), expires_at))
        
        conn.commit()
    
    def get_cached_results(self, query: str, source: str) -> Optional[List[Dict]]:
        """
        Obtiene resultados cacheados.
        
        Returns:
            Lista de resultados o None si no hay caché válido
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT results FROM search_cache 
            WHERE query = ? AND source = ? AND expires_at > ?
        """, (query, source, datetime.now()))
        
        row = cursor.fetchone()
        if row:
            return json.loads(row["results"])
        return None
    
    def clear_expired_cache(self) -> int:
        """Limpia caché expirado. Retorna número de registros eliminados."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM search_cache WHERE expires_at < ?",
            (datetime.now(),)
        )
        
        deleted = cursor.rowcount
        conn.commit()
        
        if deleted > 0:
            logger.info(f"Limpiados {deleted} registros de caché expirados")
        
        return deleted
    
    # =========================================================================
    # Keywords
    # =========================================================================
    
    def save_keyword(self, keyword: str, translation: Optional[str] = None, category: Optional[str] = None) -> None:
        """Guarda o actualiza una keyword."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO keywords (keyword, translation, category)
            VALUES (?, ?, ?)
            ON CONFLICT(keyword) DO UPDATE SET
                translation = COALESCE(?, translation),
                category = COALESCE(?, category)
        """, (keyword, translation, category, translation, category))
        
        conn.commit()
    
    def increment_keyword_search(self, keyword: str) -> None:
        """Incrementa el contador de búsqueda de una keyword."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE keywords 
            SET search_count = search_count + 1, last_searched_at = ? 
            WHERE keyword = ?
        """, (datetime.now(), keyword))
        
        conn.commit()
    
    def get_keyword_translation(self, keyword: str) -> Optional[str]:
        """Obtiene la traducción de una keyword."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT translation FROM keywords WHERE keyword = ?", (keyword,))
        row = cursor.fetchone()
        
        return row["translation"] if row else None
    
    # =========================================================================
    # Estadísticas
    # =========================================================================
    
    def get_stats(self) -> Dict[str, int]:
        """Obtiene estadísticas de la base de datos."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        cursor.execute("SELECT COUNT(*) FROM assets")
        stats["total_assets"] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM assets WHERE local_path IS NOT NULL")
        stats["downloaded_assets"] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM search_history")
        stats["total_searches"] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM keywords")
        stats["total_keywords"] = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(use_count) FROM assets")
        stats["total_uses"] = cursor.fetchone()[0] or 0
        
        return stats
