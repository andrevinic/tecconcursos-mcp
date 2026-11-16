"""Servidor MCP (stdio). A pasta de exports vem de TEC_EXPORTS_DIR."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from . import __version__, analysis
from .parsers import Biblioteca, carregar_pasta

PASTA_PADRAO = "~/TecConcursos/exports"

SOMENTE_LEITURA = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)

mcp = MCPServer(
    name="tecconcursos-mcp",
    version=__version__,
    instructions=(
        "Lê arquivos exportados do TecConcursos (CSV, XLSX, JSON ou PDF de caderno) "
        "numa pasta local e analisa o desempenho do estudante. Não acessa o site. "
        "Comece por `resumo_geral` ou `listar_exports`. Filtros de texto aceitam "
        "trechos sem acento (ex.: materia='penal')."
    ),
)

_cache: dict[str, Any] = {"assinatura": None, "bib": None}


def pasta_exports() -> Path:
    return Path(os.environ.get("TEC_EXPORTS_DIR", PASTA_PADRAO)).expanduser()


def _assinatura(pasta: Path) -> tuple:
    if not pasta.is_dir():
        return ()
    return tuple(sorted((str(p), p.stat().st_mtime_ns) for p in pasta.rglob("*") if p.is_file()))


def biblioteca() -> Biblioteca:
    """Recarrega só quando algum arquivo da pasta muda."""
    pasta = pasta_exports()
    assinatura = (str(pasta), _assinatura(pasta))
    if _cache["assinatura"] != assinatura:
        _cache["bib"] = carregar_pasta(pasta)
        _cache["assinatura"] = assinatura
    return _cache["bib"]


def _aviso_vazio(bib: Biblioteca) -> dict[str, Any] | None:
    if not bib.pasta.is_dir():
        return {"erro": f"Pasta não encontrada: {bib.pasta}. Defina TEC_EXPORTS_DIR."}
    if not bib.questoes:
        return {"erro": f"Nenhuma questão encontrada em {bib.pasta}.",
                "arquivos": [vars(a) for a in bib.arquivos]}
    return None


@mcp.tool(annotations=SOMENTE_LEITURA)
def listar_exports() -> dict[str, Any]:
    """Lista os arquivos de export encontrados, quantas questões cada um rendeu e erros de leitura."""
    bib = biblioteca()
    return {
        "pasta": str(bib.pasta),
        "pasta_existe": bib.pasta.is_dir(),
        "total_questoes": len(bib.questoes),
        "arquivos": [vars(a) for a in bib.arquivos],
    }


@mcp.tool(annotations=SOMENTE_LEITURA)
def resumo_geral() -> dict[str, Any]:
    """Visão geral: questões carregadas, respondidas, taxa de acerto e período."""
    bib = biblioteca()
    return _aviso_vazio(bib) or analysis.resumo_geral(bib.questoes)


@mcp.tool(annotations=SOMENTE_LEITURA)
def desempenho(
    agrupar_por: str = "materia",
    min_questoes: int = 1,
    materia: str | None = None,
    banca: str | None = None,
    ano: int | None = None,
) -> dict[str, Any]:
    """Taxa de acerto agrupada por materia, assunto, banca, orgao, cargo ou ano.

    Filtros opcionais restringem as questões consideradas (ex.: agrupar_por='assunto', materia='penal').
    """
    bib = biblioteca()
    if (aviso := _aviso_vazio(bib)):
        return aviso
    try:
        linhas = analysis.desempenho(bib.questoes, agrupar_por, min_questoes,
                                     materia=materia, banca=banca, ano=ano)
    except ValueError as e:
        return {"erro": str(e)}
    return {"agrupado_por": agrupar_por, "grupos": linhas}


@mcp.tool(annotations=SOMENTE_LEITURA)
def pontos_fracos(
    agrupar_por: str = "assunto",
    min_questoes: int = 5,
    limite: int = 10,
    materia: str | None = None,
    banca: str | None = None,
) -> dict[str, Any]:
    """Grupos com pior taxa de acerto, ignorando os com poucas questões (min_questoes).

    Inclui `indice_confianca` (limite inferior de Wilson) para desempatar amostras pequenas.
    """
    bib = biblioteca()
    if (aviso := _aviso_vazio(bib)):
        return aviso
    try:
        linhas = analysis.pontos_fracos(bib.questoes, agrupar_por, min_questoes, limite,
                                        materia=materia, banca=banca)
    except ValueError as e:
        return {"erro": str(e)}
    return {"agrupado_por": agrupar_por, "min_questoes": min_questoes, "pontos_fracos": linhas}


@mcp.tool(annotations=SOMENTE_LEITURA)
def questoes_erradas(
    materia: str | None = None,
    assunto: str | None = None,
    banca: str | None = None,
    ano: int | None = None,
    limite: int = 20,
) -> dict[str, Any]:
    """Questões que você errou, mais recentes primeiro — para montar revisão."""
    bib = biblioteca()
    if (aviso := _aviso_vazio(bib)):
        return aviso
    qs = analysis.questoes_erradas(bib.questoes, limite, materia=materia,
                                   assunto=assunto, banca=banca, ano=ano)
    return {"total": len(qs), "questoes": [q.resumo() for q in qs]}


@mcp.tool(annotations=SOMENTE_LEITURA)
def buscar_questao(
    termo: str,
    materia: str | None = None,
    banca: str | None = None,
    limite: int = 20,
) -> dict[str, Any]:
    """Busca por palavras (todas precisam aparecer) no código, matéria, assunto, enunciado e alternativas."""
    bib = biblioteca()
    if (aviso := _aviso_vazio(bib)):
        return aviso
    qs = analysis.buscar(bib.questoes, termo, limite, materia=materia, banca=banca)
    return {"total": len(qs), "questoes": [q.resumo(max_enunciado=1000) for q in qs]}


def main() -> None:
    mcp.run("stdio")


if __name__ == "__main__":
    main()
