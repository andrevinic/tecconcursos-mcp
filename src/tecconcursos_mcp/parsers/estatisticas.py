"""Planilhas oficiais de Estatísticas do TecConcursos.

Botões "Exportar para planilha" em *Estatísticas → Desempenho* e
*Estatísticas → Atividades*. Ambas são uma árvore matéria → assunto:

=============  ====================  ===================  ===  =====================
Hierarquia     Índice                Questões Resolvidas  ...  Quantidade de erros
=============  ====================  ===================  ===  =====================
(vazio)        Matéria Alfa          11                   ...  5
01             Tópico Um             2                    ...  2
01.01          Subtópico Um-A        1                    ...  1
=============  ====================  ===================  ===  =====================

* Desempenho: ``Acertos (%)``, ``Quantidade de acertos``, ``Erros (%)``,
  ``Quantidade de erros``, ``Peso``.
* Atividades: só ``Questões Resolvidas``.

A planilha não informa o período. Por isso a data do snapshot vem do nome do
arquivo (``desempenho_2026-11-16.xlsx``; com duas datas, a primeira é o início
do período) ou da data de modificação.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from ..models import LinhaEstatistica, Snapshot, normalizar

_DATA_NOME = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_HIERARQUIA = re.compile(r"^\d{2}(?:\.\d{2})*$")

_COLUNAS = {
    "hierarquia": "hierarquia",
    "indice": "nome",
    "questoes resolvidas": "resolvidas",
    "quantidade de acertos": "acertos",
    "quantidade de erros": "erros",
    "peso": "peso",
}


def _cabecalho(linha: Iterable[Any]) -> dict[int, str] | None:
    """Mapeia índice da coluna → campo, se a linha for o cabeçalho oficial."""
    mapa = {i: _COLUNAS[n] for i, c in enumerate(linha)
            if (n := normalizar(str(c) if c is not None else "")) in _COLUNAS}
    if {"hierarquia", "nome", "resolvidas"} <= set(mapa.values()):
        return mapa
    return None


def eh_planilha_estatisticas(primeira_linha: Iterable[Any]) -> bool:
    return _cabecalho(primeira_linha) is not None


def _int(v: Any) -> int | None:
    if v in (None, ""):
        return None
    try:
        return int(round(float(str(v).replace(",", "."))))
    except ValueError:
        return None


def _float(v: Any) -> float | None:
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def _datas_do_nome(nome: str) -> list[str]:
    saida = []
    for a, m, d in _DATA_NOME.findall(nome):
        try:
            saida.append(date(int(a), int(m), int(d)).isoformat())
        except ValueError:
            continue
    return saida


def _data_snapshot(caminho: Path) -> tuple[str, str | None]:
    datas = _datas_do_nome(caminho.name)
    if len(datas) >= 2:
        return datas[-1], datas[0]
    if datas:
        return datas[0], None
    return date.fromtimestamp(caminho.stat().st_mtime).isoformat(), None


def linhas_para_snapshot(
    linhas: Iterable[Iterable[Any]], arquivo: str, data: str,
    periodo_inicio: str | None = None,
) -> Snapshot | None:
    it = iter(linhas)
    cab = _cabecalho(next(it, ()) or ())
    if cab is None:
        return None
    campos = set(cab.values())
    # o tipo vem das colunas (a aba se chama "Desempenho"/"Atividades", mas não dependemos disso)
    tipo = "desempenho" if "acertos" in campos else "atividades"
    snap = Snapshot(arquivo=arquivo, tipo=tipo, data=data, periodo_inicio=periodo_inicio)

    materia: str | None = None
    pilha: list[str] = []  # nomes dos ancestrais, por nível
    for bruta in it:
        valores = list(bruta)
        reg = {campo: valores[i] if i < len(valores) else None for i, campo in cab.items()}
        nome = str(reg.get("nome") or "").strip()
        if not nome:
            continue
        hier = str(reg.get("hierarquia") or "").strip()
        if hier and not _HIERARQUIA.match(hier):
            continue
        if not hier:
            materia, pilha = nome, []
        elif materia is None:
            continue  # assunto sem matéria antes: planilha estranha, ignora a linha
        nivel = len(hier.split(".")) if hier else 0
        if nivel:
            pilha = pilha[: nivel - 1] + [nome]
        snap.linhas.append(LinhaEstatistica(
            materia=materia,
            nome=nome,
            hierarquia=hier,
            caminho=list(pilha),
            resolvidas=_int(reg.get("resolvidas")) or 0,
            acertos=_int(reg.get("acertos")) if tipo == "desempenho" else None,
            erros=_int(reg.get("erros")) if tipo == "desempenho" else None,
            peso=_float(reg.get("peso")),
        ))
    return snap


def ler_snapshot_xlsx(caminho: Path) -> Snapshot | None:
    """Devolve o snapshot, ou ``None`` se a planilha não for do formato oficial."""
    from openpyxl import load_workbook

    data, inicio = _data_snapshot(caminho)
    wb = load_workbook(caminho, read_only=True, data_only=True)
    try:
        for ws in wb.worksheets:
            # a planilha de Atividades vem com a dimensão errada (A1:H1); sem isso só se lê o cabeçalho
            ws.reset_dimensions()
            snap = linhas_para_snapshot(ws.iter_rows(values_only=True), caminho.name,
                                        data, inicio)
            if snap is not None:
                return snap
    finally:
        wb.close()
    return None


def primeira_linha_xlsx(caminho: Path) -> tuple[Any, ...]:
    from openpyxl import load_workbook

    wb = load_workbook(caminho, read_only=True, data_only=True)
    try:
        for ws in wb.worksheets:
            for linha in ws.iter_rows(values_only=True, max_row=1):
                return linha
    finally:
        wb.close()
    return ()
