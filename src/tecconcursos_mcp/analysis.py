"""Análises sobre a lista de questões. Funções puras, fáceis de testar."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Iterable

from .models import LinhaEstatistica, Questao, Snapshot, normalizar

AGRUPAMENTOS = ("materia", "assunto", "banca", "orgao", "cargo", "ano")


def _filtra(questoes: Iterable[Questao], **filtros: Any) -> list[Questao]:
    """Filtros de texto são 'contém', sem acento e sem diferenciar maiúsculas."""
    ativos = {k: v for k, v in filtros.items() if v not in (None, "")}
    saida = []
    for q in questoes:
        ok = True
        for campo, valor in ativos.items():
            atual = getattr(q, campo)
            if campo == "ano":
                ok = atual == int(valor)
            else:
                ok = normalizar(str(valor)) in normalizar(atual)
            if not ok:
                break
        if ok:
            saida.append(q)
    return saida


def _wilson_inferior(acertos: int, total: int, z: float = 1.96) -> float:
    """Limite inferior do intervalo de Wilson: evita que 1/1 pareça melhor que 95/100."""
    if total == 0:
        return 0.0
    p = min(max(acertos / total, 0.0), 1.0)
    centro = p + z * z / (2 * total)
    margem = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total)
    return (centro - margem) / (1 + z * z / total)


def resumo_geral(questoes: list[Questao]) -> dict[str, Any]:
    respondidas = [q for q in questoes if q.respondida]
    acertos = sum(1 for q in respondidas if q.acertou)
    datas = sorted(q.data for q in respondidas if q.data)
    contar = lambda campo: len({getattr(q, campo) for q in questoes if getattr(q, campo)})
    return {
        "questoes_carregadas": len(questoes),
        "respondidas": len(respondidas),
        "acertos": acertos,
        "erros": len(respondidas) - acertos,
        "taxa_acerto": round(acertos / len(respondidas), 4) if respondidas else None,
        "materias": contar("materia"),
        "assuntos": contar("assunto"),
        "bancas": contar("banca"),
        "periodo": {"inicio": datas[0], "fim": datas[-1]} if datas else None,
    }


def desempenho(
    questoes: list[Questao],
    agrupar_por: str = "materia",
    min_questoes: int = 1,
    **filtros: Any,
) -> list[dict[str, Any]]:
    if agrupar_por not in AGRUPAMENTOS:
        raise ValueError(f"agrupar_por deve ser um de: {', '.join(AGRUPAMENTOS)}")
    grupos: dict[Any, list[int]] = defaultdict(lambda: [0, 0])
    for q in _filtra(questoes, **filtros):
        if not q.respondida:
            continue
        chave = getattr(q, agrupar_por) or "(sem informação)"
        grupos[chave][0] += 1
        grupos[chave][1] += int(bool(q.acertou))
    linhas = [
        {
            agrupar_por: chave,
            "respondidas": total,
            "acertos": acertos,
            "erros": total - acertos,
            "taxa_acerto": round(acertos / total, 4),
        }
        for chave, (total, acertos) in grupos.items()
        if total >= min_questoes
    ]
    return sorted(linhas, key=lambda l: (-l["respondidas"], str(l[agrupar_por])))


def pontos_fracos(
    questoes: list[Questao],
    agrupar_por: str = "assunto",
    min_questoes: int = 5,
    limite: int = 10,
    **filtros: Any,
) -> list[dict[str, Any]]:
    """Ordena pelos grupos com pior desempenho *confiável* (Wilson inferior)."""
    linhas = desempenho(questoes, agrupar_por, min_questoes, **filtros)
    for l in linhas:
        l["indice_confianca"] = round(_wilson_inferior(l["acertos"], l["respondidas"]), 4)
    linhas.sort(key=lambda l: (l["taxa_acerto"], l["indice_confianca"], -l["respondidas"]))
    return linhas[:limite]


def questoes_erradas(questoes: list[Questao], limite: int = 20, **filtros: Any) -> list[Questao]:
    erradas = [q for q in _filtra(questoes, **filtros) if q.acertou is False]
    erradas.sort(key=lambda q: q.data or "", reverse=True)
    return erradas[:limite]


def buscar(questoes: list[Questao], termo: str, limite: int = 20, **filtros: Any) -> list[Questao]:
    palavras = normalizar(termo).split()
    if not palavras:
        return []
    achadas = []
    for q in _filtra(questoes, **filtros):
        alvo = normalizar(" ".join(filter(None, [
            q.id, q.materia, q.assunto, q.enunciado, " ".join(q.alternativas)
        ])))
        if all(p in alvo for p in palavras):
            achadas.append(q)
            if len(achadas) >= limite:
                break
    return achadas


# --- Planilhas oficiais de Estatísticas (snapshots) ---------------------------

ORDENS = ("fracos", "fortes", "volume")


def desempenho_assuntos(
    snap: Snapshot,
    materia: str | None = None,
    nivel: int | None = 1,
    min_questoes: int = 1,
    ordenar: str = "fracos",
    limite: int = 30,
) -> list[dict[str, Any]]:
    """Linhas de um snapshot. ``nivel=0`` são as matérias; ``1`` os assuntos de
    primeiro nível; ``None`` todos os assuntos (pais e filhos se sobrepõem)."""
    if ordenar not in ORDENS:
        raise ValueError(f"ordenar deve ser um de: {', '.join(ORDENS)}")
    alvo = normalizar(materia)
    linhas = [
        l for l in snap.linhas
        if (nivel is None and l.nivel > 0 or l.nivel == nivel)
        and l.resolvidas >= min_questoes
        and (not alvo or alvo in normalizar(l.materia))
    ]
    saida = []
    for l in linhas:
        d = l.resumo()
        if l.acertos is not None:
            d["indice_confianca"] = round(_wilson_inferior(l.acertos, l.resolvidas), 4)
        saida.append(d)
    if ordenar == "volume" or not snap.tem_acertos:
        saida.sort(key=lambda d: -d["resolvidas"])
    else:
        sinal = 1 if ordenar == "fracos" else -1
        saida.sort(key=lambda d: (sinal * d["taxa_acerto"], sinal * d["indice_confianca"], -d["resolvidas"]))
    return saida[:limite]


def _ponto(snap: Snapshot, linhas: list[LinhaEstatistica]) -> dict[str, Any]:
    resolvidas = sum(l.resolvidas for l in linhas)
    p: dict[str, Any] = {"data": snap.data, "tipo": snap.tipo, "arquivo": snap.arquivo,
                         "resolvidas": resolvidas}
    if snap.periodo_inicio:
        p["periodo_inicio"] = snap.periodo_inicio
    if snap.tem_acertos:
        acertos = sum(l.acertos or 0 for l in linhas)
        p["acertos"] = acertos
        p["erros"] = resolvidas - acertos
        p["taxa_acerto"] = round(acertos / resolvidas, 4) if resolvidas else None
    return p


def progresso(snapshots: list[Snapshot], materia: str | None = None, fonte: str = "tec") -> dict[str, Any]:
    """Série temporal: um ponto por snapshot (planilha do TEC ou dia do QConcursos), no total e por matéria."""
    alvo = normalizar(materia)
    ordenados = sorted((s for s in snapshots if s.fonte == fonte), key=lambda s: (s.data, s.arquivo))
    geral, por_materia = [], defaultdict(list)
    for s in ordenados:
        mats = [l for l in s.materias() if not alvo or alvo in normalizar(l.materia)]
        if not mats:
            continue
        geral.append(_ponto(s, mats))
        for l in mats:
            por_materia[l.materia].append(_ponto(s, [l]))

    def variacao(pontos: list[dict[str, Any]]) -> dict[str, Any] | None:
        com_taxa = [p for p in pontos if p.get("taxa_acerto") is not None]
        if len(com_taxa) < 2:
            return None
        a, b = com_taxa[0], com_taxa[-1]
        return {"de": a["data"], "ate": b["data"],
                "taxa_inicial": a["taxa_acerto"], "taxa_final": b["taxa_acerto"],
                "diferenca_pontos": round((b["taxa_acerto"] - a["taxa_acerto"]) * 100, 1)}

    return {
        "fonte": fonte,
        "snapshots": len(geral),
        "geral": geral,
        "variacao_geral": variacao(geral),
        "materias": {m: {"pontos": p, "variacao": variacao(p)} for m, p in sorted(por_materia.items())},
    }


def totais(snapshots: list[Snapshot], fonte: str = "qconcursos", nivel: int = 0,
           materia: str | None = None) -> list[dict[str, Any]]:
    """Soma snapshots que não se sobrepõem (um por dia, como os do QConcursos).

    nivel=0 soma por disciplina; nivel=1 soma por assunto.
    """
    alvo = normalizar(materia)
    soma: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    for s in snapshots:
        if s.fonte != fonte:
            continue
        for l in s.linhas:
            if l.nivel == nivel and l.acertos is not None and (not alvo or alvo in normalizar(l.materia if nivel == 0 else l.nome)):
                soma[(l.materia, l.nome)][0] += l.resolvidas
                soma[(l.materia, l.nome)][1] += l.acertos
    linhas = []
    for (mat, nome), (tot, ac) in soma.items():
        d = {"materia" if nivel == 0 else "assunto": nome if nivel else mat, "resolvidas": tot,
             "acertos": ac, "erros": tot - ac, "taxa_acerto": round(ac / tot, 4) if tot else None,
             "indice_confianca": round(_wilson_inferior(ac, tot), 4)}
        linhas.append(d)
    return sorted(linhas, key=lambda d: -d["resolvidas"])
