"""Modelo único de questão, independente do formato do arquivo exportado."""

from __future__ import annotations

import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Questao:
    id: str | None = None
    materia: str | None = None
    assunto: str | None = None
    banca: str | None = None
    orgao: str | None = None
    cargo: str | None = None
    ano: int | None = None
    enunciado: str | None = None
    alternativas: list[str] = field(default_factory=list)
    gabarito: str | None = None
    resposta: str | None = None
    acertou: bool | None = None
    data: str | None = None
    arquivo: str | None = None

    def __post_init__(self) -> None:
        # Se o export não traz "acertou" mas traz gabarito e resposta, deduz.
        if self.acertou is None and self.gabarito and self.resposta:
            self.acertou = normalizar(self.gabarito) == normalizar(self.resposta)

    @property
    def respondida(self) -> bool:
        return self.acertou is not None

    def resumo(self, max_enunciado: int = 300) -> dict[str, Any]:
        d = asdict(self)
        if d["enunciado"] and len(d["enunciado"]) > max_enunciado:
            d["enunciado"] = d["enunciado"][:max_enunciado].rstrip() + "…"
        return {k: v for k, v in d.items() if v not in (None, [], "")}


def normalizar(texto: str | None) -> str:
    """Minúsculas, sem acentos e sem espaços extras — para comparar e buscar."""
    if not texto:
        return ""
    sem_acento = unicodedata.normalize("NFKD", str(texto))
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(sem_acento.lower().split())
