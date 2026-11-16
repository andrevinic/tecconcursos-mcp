"""Análises sobre a lista de questões. Funções puras, fáceis de testar."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Iterable

from .models import Questao, normalizar

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
    p = acertos / total
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
