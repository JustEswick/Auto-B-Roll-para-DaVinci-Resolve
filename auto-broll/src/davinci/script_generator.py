"""
Generador de Scripts para DaVinci Resolve.

Genera scripts Python que se pueden ejecutar DENTRO de DaVinci Resolve
para importar assets al Media Pool y colocarlos en el timeline.
Esto funciona tanto con DaVinci Free como Studio.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class BRollClip:
    """Información de un clip de B-Roll para insertar."""
    asset_path: str          # Ruta absoluta al archivo
    keyword: str             # Keyword del concepto
    start_time: float        # Tiempo de inicio en segundos
    end_time: float          # Tiempo de fin en segundos
    duration: float          # Duración del clip en el timeline
    track_index: int = 2     # Track donde insertar (2 = encima del video principal)


@dataclass
class ImportJob:
    """Trabajo de importación para DaVinci."""
    project_name: str
    clips: List[BRollClip]
    target_track: int = 2
    frame_rate: float = 24.0
    
    def to_json(self, path: Path) -> None:
        """Guarda el job como JSON."""
        data = {
            "project_name": self.project_name,
            "target_track": self.target_track,
            "frame_rate": self.frame_rate,
            "clips": [asdict(c) for c in self.clips]
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, path: Path) -> "ImportJob":
        """Carga un job desde JSON."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        clips = [BRollClip(**c) for c in data["clips"]]
        return cls(
            project_name=data["project_name"],
            clips=clips,
            target_track=data.get("target_track", 2),
            frame_rate=data.get("frame_rate", 24.0)
        )


class DaVinciScriptGenerator:
    """
    Genera scripts Python para ejecutar dentro de DaVinci Resolve.
    
    Los scripts generados:
    1. Importan assets al Media Pool
    2. Crean un bin organizado por keywords
    3. Insertan clips en el timeline en los timecodes correctos
    """
    
    SCRIPT_TEMPLATE = '''#!/usr/bin/env python
"""
Auto-B-Roll Import Script
Generado automáticamente por Auto-B-Roll

Este script importa los assets de B-Roll al proyecto actual
y los coloca en el timeline.

INSTRUCCIONES:
1. Abre DaVinci Resolve con tu proyecto
2. Ve a Workspace > Scripts > {script_name}
3. Los clips se importarán automáticamente

Fecha: {date}
Proyecto: {project_name}
"""

import os

# Datos de importación embebidos
IMPORT_DATA = {import_data_json}

def main():
    print("=" * 50)
    print("AUTO-B-ROLL IMPORT SCRIPT")
    print("=" * 50)
    
    # En scripts internos de DaVinci, 'resolve' ya está disponible
    try:
        res = resolve
    except NameError:
        print("ERROR: Variable 'resolve' no disponible.")
        print("Este script debe ejecutarse desde:")
        print("  DaVinci Resolve > Workspace > Scripts > Edit")
        return
    
    if not res:
        print("ERROR: resolve es None")
        return
    
    print("OK: Conexion con Resolve establecida")
    
    pm = res.GetProjectManager()
    if not pm:
        print("ERROR: No se pudo obtener ProjectManager")
        return
    
    project = pm.GetCurrentProject()
    if not project:
        print("ERROR: No hay proyecto abierto")
        print("Abre un proyecto primero")
        return
    
    print(f"OK: Proyecto: {{project.GetName()}}")
    
    media_pool = project.GetMediaPool()
    if not media_pool:
        print("ERROR: No se pudo obtener MediaPool")
        return
    
    timeline = project.GetCurrentTimeline()
    if not timeline:
        print("AVISO: No hay timeline activo (opcional)")
    else:
        print(f"OK: Timeline: {{timeline.GetName()}}")
    
    clips = IMPORT_DATA.get("clips", [])
    print(f"Clips a procesar: {{len(clips)}}")
    print("-" * 50)
    
    if not clips:
        print("No hay clips para importar")
        return
    
    # Obtener o crear carpeta Auto-B-Roll
    root_folder = media_pool.GetRootFolder()
    broll_bin = None
    
    subfolders = root_folder.GetSubFolderList()
    if subfolders:
        for sf in subfolders:
            if sf.GetName() == "Auto-B-Roll":
                broll_bin = sf
                print("Usando bin existente: Auto-B-Roll")
                break
    
    if not broll_bin:
        broll_bin = media_pool.AddSubFolder(root_folder, "Auto-B-Roll")
        if broll_bin:
            print("Creado nuevo bin: Auto-B-Roll")
        else:
            print("AVISO: No se pudo crear bin, usando root")
    
    if broll_bin:
        media_pool.SetCurrentFolder(broll_bin)
    
    # Importar archivos y guardar referencia
    imported = 0
    failed = 0
    imported_items = []  # Lista de (mediaPoolItem, clip_data)
    
    for clip_data in clips:
        asset_path = clip_data.get("asset_path", "")
        
        if not asset_path:
            print("X Sin ruta de archivo")
            failed += 1
            continue
        
        # Verificar si existe
        if not os.path.exists(asset_path):
            print(f"X No existe: {{os.path.basename(asset_path)}}")
            failed += 1
            continue
        
        # Intentar importar
        result = media_pool.ImportMedia([asset_path])
        
        if result and len(result) > 0:
            print(f"+ {{os.path.basename(asset_path)}}")
            imported += 1
            imported_items.append((result[0], clip_data))
        else:
            print(f"X Error: {{os.path.basename(asset_path)}}")
            failed += 1
    
    print("-" * 50)
    print(f"Importados: {{imported}}, Fallidos: {{failed}}")
    
    if not imported_items:
        print("No se importaron archivos.")
        return
    
    # Insertar en timeline
    if not timeline:
        print("")
        print("No hay timeline activo.")
        print("Los assets estan en Media Pool > Auto-B-Roll")
        print("Cralos manualmente al timeline")
        return
    
    print("")
    print("Insertando en timeline...")
    
    # Obtener FPS del timeline
    fps = 24.0
    try:
        fps_str = timeline.GetSetting("timelineFrameRate")
        if fps_str:
            fps = float(fps_str.replace(" DF", ""))
    except:
        pass
    
    print(f"FPS: {{fps}}")
    
    # Obtener frame de inicio del timeline
    timeline_start = timeline.GetStartFrame()
    print(f"Timeline start frame: {{timeline_start}}")
    
    target_track = IMPORT_DATA.get("target_track", 2)
    
    # Asegurar que existe el track
    current_video_tracks = timeline.GetTrackCount("video")
    while current_video_tracks < target_track:
        timeline.AddTrack("video")
        current_video_tracks += 1
        print(f"Creado video track {{current_video_tracks}}")
    
    print(f"Target: Video Track {{target_track}}")
    print("")
    
    inserted = 0
    
    for mpi, clip_data in imported_items:
        start_time = clip_data.get("start_time", 0)
        duration = clip_data.get("duration", 3.0)
        
        # Calcular frames (relativo al inicio del timeline)
        record_frame = timeline_start + int(start_time * fps)
        duration_frames = int(duration * fps)
        
        # Si la duracion es 0, usar al menos 1 segundo
        if duration_frames < 1:
            duration_frames = int(fps)
        
        # Crear clip info para AppendToTimeline
        clip_info = {{
            "mediaPoolItem": mpi,
            "startFrame": 0,
            "endFrame": duration_frames,
            "trackIndex": target_track,
            "recordFrame": record_frame
        }}
        
        keyword = clip_data.get("keyword", "unknown")[:20]
        
        # Insertar
        result = media_pool.AppendToTimeline([clip_info])
        
        if result:
            print(f"+ {{keyword}} @ frame {{record_frame}} ({{start_time:.1f}}s)")
            inserted += 1
        else:
            print(f"X {{keyword}} @ frame {{record_frame}}")
    
    print("-" * 50)
    print(f"RESULTADO: {{inserted}} clips en Track {{target_track}}")
    
    if inserted > 0:
        print("")
        print("Si no ves los clips, ve al inicio del timeline")
        print("o presiona Home para ir al frame 0")
    
    print("=" * 50)
    print("FIN DEL SCRIPT")
    print("=" * 50)

# Ejecutar al cargar
main()
'''
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Inicializa el generador.
        
        Args:
            output_dir: Directorio donde guardar scripts y datos.
                       Si es None, usa directorio temporal.
        """
        if output_dir is None:
            from src.config import CACHE_DIR
            output_dir = CACHE_DIR / "davinci_scripts"
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_script(
        self,
        job: ImportJob,
        script_name: str = "auto_broll_import"
    ) -> Path:
        """
        Genera un script de importación para DaVinci.
        
        Args:
            job: Trabajo de importación con los clips
            script_name: Nombre del script (sin extensión)
            
        Returns:
            Ruta al script generado
        """
        from datetime import datetime
        
        # Preparar datos JSON embebidos
        import_data = {
            "project_name": job.project_name,
            "target_track": job.target_track,
            "frame_rate": job.frame_rate,
            "clips": [asdict(c) for c in job.clips]
        }
        
        # Generar script
        script_content = self.SCRIPT_TEMPLATE.format(
            script_name=script_name,
            date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            project_name=job.project_name,
            import_data_json=json.dumps(import_data, indent=2, ensure_ascii=False)
        )
        
        # Guardar script
        script_path = self.output_dir / f"{script_name}.py"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        
        logger.info(f"Script generado: {script_path}")
        
        return script_path
    
    def get_davinci_scripts_folder(self) -> Path:
        """
        Obtiene la carpeta de scripts de DaVinci Resolve.
        
        La estructura de carpetas en DaVinci Resolve 20 es:
        Support/Fusion/Scripts/
            ├── Color/
            ├── Comp/
            ├── Delivery/
            ├── Edit/      <- Usamos esta para timeline
            ├── Tool/
            ├── Utility/
            └── Views/
        
        Creamos una subcarpeta Auto-B-Roll dentro de Edit.
        
        Returns:
            Ruta a la carpeta de scripts (Edit/Auto-B-Roll)
        """
        import os
        
        # Windows - AppData/Roaming
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            # Ruta correcta para DaVinci Resolve 20
            base_scripts = Path(appdata) / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Fusion" / "Scripts"
            # Usar Edit porque es para operaciones de timeline
            scripts_folder = base_scripts / "Edit" / "Auto-B-Roll"
            return scripts_folder
        
        # Fallback
        return self.output_dir
    
    def install_script(self, script_path: Path) -> Path:
        """
        Copia un script a la carpeta de scripts de DaVinci.
        
        Args:
            script_path: Ruta al script a instalar
            
        Returns:
            Ruta donde se instaló el script
        """
        import shutil
        
        target_folder = self.get_davinci_scripts_folder()
        target_folder.mkdir(parents=True, exist_ok=True)
        
        target_path = target_folder / script_path.name
        shutil.copy2(script_path, target_path)
        
        logger.info(f"Script instalado en: {target_path}")
        
        return target_path


def create_import_job_from_search_results(
    search_results: Dict[str, list],
    downloaded_assets: Dict[str, Path],
    analysis_result,
    project_name: str = "Auto-B-Roll Project"
) -> ImportJob:
    """
    Crea un ImportJob a partir de resultados de búsqueda y assets descargados.
    
    Args:
        search_results: Dict {keyword: [StockAsset, ...]}
        downloaded_assets: Dict {asset_id: local_path}
        analysis_result: Resultado del análisis semántico
        project_name: Nombre del proyecto
        
    Returns:
        ImportJob listo para generar script
    """
    clips = []
    
    # Obtener conceptos del análisis para los timestamps
    concept_times = {}
    for concept in analysis_result.concepts:
        if concept.primary_search_term not in concept_times:
            concept_times[concept.primary_search_term] = {
                "start": concept.start_time,
                "end": concept.end_time
            }
    
    # Crear clips para cada asset descargado
    for keyword, assets in search_results.items():
        for asset in assets:
            if asset.id in downloaded_assets:
                local_path = downloaded_assets[asset.id]
                
                # Obtener timestamps del concepto
                times = concept_times.get(keyword, {"start": 0, "end": 5})
                
                clip = BRollClip(
                    asset_path=str(local_path),
                    keyword=keyword,
                    start_time=times["start"],
                    end_time=times["end"],
                    duration=min(times["end"] - times["start"], 5.0),  # Máximo 5 segundos
                    track_index=2
                )
                clips.append(clip)
                break  # Solo un asset por keyword
    
    return ImportJob(
        project_name=project_name,
        clips=clips,
        target_track=2,
        frame_rate=24.0
    )
