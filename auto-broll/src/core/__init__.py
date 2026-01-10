"""
Módulo Core - Orquestación y Pipeline.

Este módulo coordina el flujo de procesamiento de Auto-B-Roll.
"""

from .orchestrator import Orchestrator
from .audio_extractor import AudioExtractor
from .pipeline import Pipeline, PipelineState

__all__ = [
    "Orchestrator",
    "AudioExtractor", 
    "Pipeline",
    "PipelineState",
]
