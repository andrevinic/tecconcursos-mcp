"""Registro de parsers por extensão e carregamento da pasta de exports."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..models import Questao, Snapshot
from .estatisticas import eh_planilha_estatisticas, ler_snapshot_xlsx, primeira_linha_xlsx
from .pdf import ler_pdf
from .tabular import ler_csv, ler_json, ler_xlsx

PARSERS: dict[str, Callable[[Path], list[Questao]]] = {
    ".csv": ler_csv,
    ".tsv": ler_csv,
    ".xlsx": ler_xlsx,
    ".json": ler_json,
    ".pdf": ler_pdf,
}


@dataclass
class ResultadoArquivo:
    arquivo: str
    formato: str
    questoes: int = 0
    erro: str | None = None
    snapshot: str | None = None  # "desempenho"/"atividades" quando é a planilha oficial
    data: str | None = None


@dataclass
class Biblioteca:
    pasta: Path
    questoes: list[Questao] = field(default_factory=list)
    arquivos: list[ResultadoArquivo] = field(default_factory=list)
    snapshots: list[Snapshot] = field(default_factory=list)

    def ultimo_snapshot(self, tipo: str | None = "desempenho") -> Snapshot | None:
        candidatos = [s for s in self.snapshots if tipo is None or s.tipo == tipo]
        return max(candidatos, key=lambda s: (s.data, s.arquivo), default=None)


def carregar_pasta(pasta: Path) -> Biblioteca:
    bib = Biblioteca(pasta=pasta)
    if not pasta.is_dir():
        return bib
    for caminho in sorted(p for p in pasta.rglob("*") if p.is_file()):
        parser = PARSERS.get(caminho.suffix.lower())
        if parser is None or caminho.name.startswith((".", "~$")):
            continue
        res = ResultadoArquivo(arquivo=str(caminho.relative_to(pasta)), formato=caminho.suffix.lower()[1:])
        try:
            if caminho.suffix.lower() == ".xlsx" and eh_planilha_estatisticas(primeira_linha_xlsx(caminho)):
                snap = ler_snapshot_xlsx(caminho)
                if snap is not None:
                    res.snapshot, res.data = snap.tipo, snap.data
                    bib.snapshots.append(snap)
                    bib.arquivos.append(res)
                    continue
            qs = parser(caminho)
            res.questoes = len(qs)
            bib.questoes.extend(qs)
        except Exception as e:  # um arquivo ruim não derruba os demais
            res.erro = f"{type(e).__name__}: {e}"
        bib.arquivos.append(res)
    bib.questoes = _deduplicar(bib.questoes)
    bib.snapshots.sort(key=lambda s: (s.data, s.arquivo))
    return bib


def _deduplicar(questoes: list[Questao]) -> list[Questao]:
    """Mesma questão em vários exports: fica a versão com mais informação,
    priorizando a que tem resultado (acertou/errou)."""
    vistas: dict[str, Questao] = {}
    sem_id: list[Questao] = []
    for q in questoes:
        if not q.id or "#" in q.id:
            sem_id.append(q)
            continue
        atual = vistas.get(q.id)
        if atual is None or _peso(q) > _peso(atual):
            vistas[q.id] = q
    return list(vistas.values()) + sem_id


def _peso(q: Questao) -> int:
    return (10 if q.respondida else 0) + sum(
        1 for v in (q.materia, q.assunto, q.banca, q.enunciado, q.gabarito) if v
    )
