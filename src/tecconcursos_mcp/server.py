"""Servidor MCP (stdio). A pasta de exports vem de TEC_EXPORTS_DIR."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from . import __version__, analysis, mentoria
from .parsers import Biblioteca, carregar_pasta

PASTA_PADRAO = "~/TecConcursos/exports"

SOMENTE_LEITURA = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)

mcp = MCPServer(
    name="tecconcursos-mcp",
    version=__version__,
    instructions=(
        "Lê arquivos exportados do TecConcursos numa pasta local e analisa o desempenho "
        "do estudante. Não acessa o site. Há dois tipos de dado: (1) planilhas oficiais de "
        "Estatísticas (Desempenho/Atividades), resumos por matéria e assunto, uma por data; "
        "use `desempenho_assuntos` e `progresso`; (2) exports por questão (CSV/JSON/PDF de "
        "caderno); use `desempenho`, `pontos_fracos`, `questoes_erradas`, `buscar_questao`. "
        "Comece por `resumo_geral`. Filtros de texto aceitam trechos sem acento (ex.: materia='penal')."
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


def _aviso_vazio(bib: Biblioteca, precisa: str = "questoes") -> dict[str, Any] | None:
    if not bib.pasta.is_dir():
        return {"erro": f"Pasta não encontrada: {bib.pasta}. Defina TEC_EXPORTS_DIR."}
    if precisa == "questoes" and not bib.questoes:
        dica = (" Há planilhas de Estatísticas: use `desempenho_assuntos` e `progresso`."
                if bib.snapshots else "")
        return {"erro": f"Nenhum export por questão encontrado em {bib.pasta}.{dica}",
                "arquivos": [vars(a) for a in bib.arquivos]}
    if precisa == "snapshots" and not bib.snapshots:
        return {"erro": (f"Nenhuma planilha de Estatísticas em {bib.pasta}. No site, vá em "
                         "Estatísticas → Desempenho, marque 'Selecionar Todos' e clique em "
                         "'Exportar para planilha'; depois rode `tecconcursos-mcp importar`."),
                "arquivos": [vars(a) for a in bib.arquivos]}
    if precisa == "qualquer" and not bib.questoes and not bib.snapshots:
        return {"erro": f"Nenhum export encontrado em {bib.pasta}.",
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
        "planilhas_estatisticas": len(bib.snapshots),
        "arquivos": [{k: v for k, v in vars(a).items() if v is not None} for a in bib.arquivos],
    }


@mcp.tool(annotations=SOMENTE_LEITURA)
def resumo_geral() -> dict[str, Any]:
    """Visão geral: última planilha de Estatísticas (por matéria) e/ou exports por questão."""
    bib = biblioteca()
    if (aviso := _aviso_vazio(bib, "qualquer")):
        return aviso
    saida: dict[str, Any] = {}
    if (snap := bib.ultimo_snapshot("desempenho") or bib.ultimo_snapshot("atividades")):
        mats = analysis.desempenho_assuntos(snap, nivel=0, ordenar="volume", limite=1000)
        resolvidas = sum(m["resolvidas"] for m in mats)
        estat: dict[str, Any] = {"arquivo": snap.arquivo, "tipo": snap.tipo, "data": snap.data,
                                 "resolvidas": resolvidas, "materias": mats,
                                 "planilhas_carregadas": len(bib.snapshots)}
        if snap.tem_acertos and resolvidas:
            estat["taxa_acerto"] = round(sum(m["acertos"] for m in mats) / resolvidas, 4)
        saida["estatisticas_tec"] = estat
    if bib.questoes:
        saida["exports_por_questao"] = analysis.resumo_geral(bib.questoes)
    return saida


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


@mcp.tool(annotations=SOMENTE_LEITURA)
def desempenho_assuntos(
    materia: str | None = None,
    nivel: int | None = 1,
    min_questoes: int = 1,
    ordenar: str = "fracos",
    limite: int = 30,
) -> dict[str, Any]:
    """Acertos por matéria/assunto na planilha de Desempenho mais recente.

    nivel: 0 = matérias, 1 = assuntos de 1º nível (padrão), 2+ = subassuntos; None = todos.
    ordenar: 'fracos' (pior taxa primeiro, com Wilson para desempatar), 'fortes' ou 'volume'.
    """
    bib = biblioteca()
    if (aviso := _aviso_vazio(bib, "snapshots")):
        return aviso
    snap = bib.ultimo_snapshot("desempenho") or bib.ultimo_snapshot("atividades")
    try:
        linhas = analysis.desempenho_assuntos(snap, materia, nivel, min_questoes, ordenar, limite)
    except ValueError as e:
        return {"erro": str(e)}
    saida: dict[str, Any] = {"arquivo": snap.arquivo, "data": snap.data, "tipo": snap.tipo,
                             "linhas": linhas}
    if not snap.tem_acertos:
        saida["aviso"] = "Planilha de Atividades só tem contagem; exporte a de Desempenho para ver acertos."
    return saida


@mcp.tool(annotations=SOMENTE_LEITURA)
def progresso(materia: str | None = None) -> dict[str, Any]:
    """Evolução ao longo das planilhas exportadas: um ponto por planilha, no total e por matéria.

    Cada planilha cobre o período escolhido no site na hora de exportar. Para comparar
    pontos, exporte sempre com o mesmo tipo de período (ex.: últimos 7 dias, toda semana).
    """
    bib = biblioteca()
    if (aviso := _aviso_vazio(bib, "snapshots")):
        return aviso
    return analysis.progresso(bib.snapshots, materia)


@mcp.tool(annotations=SOMENTE_LEITURA)
def preparar_lancamentos_mentoria(metas: list[str]) -> dict[str, Any]:
    """Calcula o que lançar nas Metas Diárias da mentoria a partir da planilha de Desempenho mais recente.

    `metas`: títulos das metas de hoje ainda não concluídas, como aparecem na página
    (ex.: ["Simulado de Informática", "Simulado de Direito Constitucional (VTM)"]).
    Não acessa a mentoria: só devolve, por meta, a matéria do TecConcursos casada e as questões/acertos.
    Mostre o resultado ao usuário e peça confirmação antes de preencher qualquer coisa.
    """
    bib = biblioteca()
    if not bib.pasta.is_dir():
        return {"erro": f"Pasta não encontrada: {bib.pasta}. Defina TEC_EXPORTS_DIR."}
    return mentoria.preparar(bib.ultimo_snapshot("desempenho"), metas, bib.pasta)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False,
                                      idempotentHint=False, openWorldHint=False))
def registrar_lancamentos_mentoria(planilha: str, lancamentos: list[dict[str, Any]]) -> dict[str, Any]:
    """Anota localmente (mentoria_lancados.json) o que JÁ foi salvo na mentoria, para não lançar de novo.

    `planilha`: o campo `planilha` devolvido por `preparar_lancamentos_mentoria`.
    `lancamentos`: itens efetivamente salvos, cada um com meta, materia_tec, questoes e acertos.
    """
    bib = biblioteca()
    if planilha not in {s.arquivo for s in bib.snapshots}:
        return {"erro": f"Planilha desconhecida: {planilha}"}
    faltando = [i for i in lancamentos if not {"materia_tec", "questoes", "acertos"} <= set(i)]
    if faltando:
        return {"erro": "Cada lançamento precisa de materia_tec, questoes e acertos.", "itens": faltando}
    return mentoria.registrar(bib.pasta, planilha, lancamentos)


@mcp.prompt(name="lancar_metas_mentoria", title="Lançar desempenho do TEC nas metas da mentoria")
def lancar_metas_mentoria() -> str:
    """Roteiro: ler as metas de hoje, preparar, confirmar com o usuário, preencher e registrar."""
    url = "a página de Metas Diárias da sua mentoria"
    cfg = pasta_exports() / mentoria.ARQ_MAPA
    if cfg.is_file():
        try:
            url = json.loads(cfg.read_text(encoding="utf-8")).get("url") or url
        except ValueError:
            pass
    return mentoria.ROTEIRO.format(url=url)


def main() -> None:
    from .cli import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()
