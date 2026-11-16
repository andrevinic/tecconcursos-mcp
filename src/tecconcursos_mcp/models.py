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


@dataclass
class LinhaEstatistica:
    """Uma linha da planilha oficial de Estatísticas (matéria ou assunto).

    ``hierarquia`` é vazia para a linha da matéria e ``"01.02"`` para assuntos;
    ``nivel`` é 0 para a matéria, 1 para ``"01"``, 2 para ``"01.02"`` etc.
    ``acertos``/``erros`` ficam ``None`` no export de Atividades, que só tem contagem.
    """

    materia: str
    nome: str
    hierarquia: str = ""
    caminho: list[str] = field(default_factory=list)
    resolvidas: int = 0
    acertos: int | None = None
    erros: int | None = None
    peso: float | None = None

    @property
    def nivel(self) -> int:
        return len(self.hierarquia.split(".")) if self.hierarquia else 0

    @property
    def taxa_acerto(self) -> float | None:
        if self.acertos is None or not self.resolvidas:
            return None
        return round(self.acertos / self.resolvidas, 4)

    def resumo(self) -> dict[str, Any]:
        d = {
            "materia": self.materia,
            "assunto": self.nome if self.nivel else None,
            "hierarquia": self.hierarquia or None,
            "caminho": " > ".join(self.caminho) if self.nivel > 1 else None,
            "resolvidas": self.resolvidas,
            "acertos": self.acertos,
            "erros": self.erros,
            "taxa_acerto": self.taxa_acerto,
        }
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class Snapshot:
    """Uma planilha exportada de Estatísticas → Desempenho ou → Atividades.

    A planilha não diz o período que cobre: ``data`` vem do nome do arquivo
    (``AAAA-MM-DD``) ou, na falta, da data de modificação do arquivo.
    """

    arquivo: str
    tipo: str  # "desempenho" | "atividades"
    data: str  # ISO AAAA-MM-DD
    periodo_inicio: str | None = None
    linhas: list[LinhaEstatistica] = field(default_factory=list)

    @property
    def tem_acertos(self) -> bool:
        return self.tipo == "desempenho"

    def materias(self) -> list[LinhaEstatistica]:
        return [l for l in self.linhas if l.nivel == 0]


def normalizar(texto: str | None) -> str:
    """Minúsculas, sem acentos e sem espaços extras — para comparar e buscar."""
    if not texto:
        return ""
    sem_acento = unicodedata.normalize("NFKD", str(texto))
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(sem_acento.lower().split())
