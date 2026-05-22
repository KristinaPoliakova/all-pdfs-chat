from __future__ import annotations

from app.config.settings import Settings, get_settings
from app.parsing.azure_di import AzureDocumentIntelligenceParser
from app.parsing.composite import CompositeDocumentParser
from app.parsing.protocol import DocumentParser


def create_document_parser(settings: Settings | None = None) -> DocumentParser:
    cfg = settings or get_settings()
    azure_parser = None
    if cfg.parsing_enabled and cfg.azure_document_intelligence_endpoint.strip():
        azure_parser = AzureDocumentIntelligenceParser(settings=cfg)
    return CompositeDocumentParser(settings=cfg, azure_parser=azure_parser)
