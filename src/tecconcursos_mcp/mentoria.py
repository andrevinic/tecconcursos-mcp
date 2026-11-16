"""Preparar lançamentos de questões para as Metas Diárias de uma mentoria (plataforma Tutory).

O servidor **não acessa a mentoria**. Ele só:

1. recebe os nomes das metas do dia (lidos da página pelo cliente/usuário);
2. casa cada meta com uma matéria da planilha de Desempenho mais recente;
3. devolve quantas questões e acertos lançar em cada meta;
4. depois que o lançamento é feito na página, registra o que foi lançado
   (``mentoria_lancados.json``) para não lançar a mesma planilha duas vezes.

Nomes diferentes entre os sites ("Língua Portuguesa (VTM)" × "Língua Portuguesa
(Português)") são casados pelo nome-base. Para forçar um par, crie ``mentoria.json``
na pasta de exports::

    {"materias": {"Informática": "Noções de Informática"}}

(chave = matéria da meta; valor = matéria do TecConcursos).
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .models import Snapshot, normalizar

ARQ_MAPA = "mentoria.json"
ARQ_REGISTRO = "mentoria_lancados.json"

_PREFIXOS = re.compile(r"^(simulado|revisao|exercicios|estudo|questoes|leitura)\s+(de|da|do|das|dos)\s+")
_PARENTESES = re.compile(r"\s*\([^)]*\)")
_NOCOES = re.compile(r"^nocoes\s+(de|da|do)\s+")


def nome_base(nome: str) -> str:
    """'Simulado de Língua Portuguesa (VTM)' → 'lingua portuguesa'."""
    n = normalizar(nome)
    n = _PREFIXOS.sub("", n)
    n = _PARENTESES.sub("", n)
    n = _NOCOES.sub("", n)
    return " ".join(n.split())


def ler_mapa(pasta: Path) -> dict[str, str]:
    p = pasta / ARQ_MAPA
    if not p.is_file():
        return {}
    dados = json.loads(p.read_text(encoding="utf-8"))
    return {normalizar(k): v for k, v in (dados.get("materias") or {}).items()}


def ler_registro(pasta: Path) -> list[dict[str, Any]]:
    p = pasta / ARQ_REGISTRO
    if not p.is_file():
        return []
    return json.loads(p.read_text(encoding="utf-8")).get("lancamentos", [])


def casar(meta: str, materias_tec: list[str], mapa: dict[str, str]) -> str | None:
    """Matéria do TecConcursos que corresponde à meta, ou None se ambíguo/ausente."""
    for chave in (normalizar(meta), nome_base(meta)):
        if chave in mapa:
            alvo = normalizar(mapa[chave])
            return next((m for m in materias_tec if normalizar(m) == alvo), None)
    base = nome_base(meta)
    if not base:
        return None
    iguais = [m for m in materias_tec if nome_base(m) == base]
    if len(iguais) == 1:
        return iguais[0]
    contem = [m for m in materias_tec if base in nome_base(m) or nome_base(m) in base]
    return contem[0] if len(contem) == 1 else None


def preparar(snap: Snapshot | None, metas: list[str], pasta: Path,
             hoje: date | None = None) -> dict[str, Any]:
    if snap is None or not snap.tem_acertos:
        return {"erro": "Nenhuma planilha de Desempenho na pasta. No TecConcursos: Estatísticas → "
                        "Desempenho, período = desde o último lançamento (ex.: hoje), Selecionar Todos, "
                        "Exportar para planilha; depois `tecconcursos-mcp importar`."}
    hoje = hoje or date.today()
    mapa = ler_mapa(pasta)
    ja = {(r["arquivo"], r["materia_tec"]) for r in ler_registro(pasta)}
    por_materia = {l.materia: l for l in snap.materias()}
    nomes_tec = list(por_materia)

    lancar, ignorar, usadas = [], [], set()
    for meta in metas:
        tec = casar(meta, nomes_tec, mapa)
        if tec is None:
            ignorar.append({"meta": meta, "motivo": "matéria não encontrada na planilha (sem questões "
                                                    f"nela, ou nome diferente: indique o par em {ARQ_MAPA})"})
            continue
        usadas.add(tec)
        linha = por_materia[tec]
        if (snap.arquivo, tec) in ja:
            ignorar.append({"meta": meta, "materia_tec": tec, "motivo": "esta planilha já foi lançada para essa matéria"})
        elif not linha.resolvidas:
            ignorar.append({"meta": meta, "materia_tec": tec, "motivo": "nenhuma questão dessa matéria na planilha"})
        else:
            lancar.append({"meta": meta, "materia_tec": tec,
                           "questoes": linha.resolvidas, "acertos": linha.acertos or 0})

    sem_meta = [{"materia_tec": m, "questoes": l.resolvidas, "acertos": l.acertos}
                for m, l in por_materia.items() if m not in usadas and l.resolvidas
                and (snap.arquivo, m) not in ja]
    avisos = []
    if snap.data != hoje.isoformat():
        avisos.append(f"A planilha é de {snap.data}; a mentoria registra com a data de hoje ({hoje.isoformat()}).")
    avisos.append("A planilha não informa o período: confirme que ela cobre só o que ainda não foi lançado.")
    return {"planilha": snap.arquivo, "data_planilha": snap.data, "lancar": lancar,
            "ignorados": ignorar, "materias_tec_sem_meta_hoje": sem_meta, "avisos": avisos}


def registrar(pasta: Path, arquivo: str, lancamentos: list[dict[str, Any]]) -> dict[str, Any]:
    p = pasta / ARQ_REGISTRO
    registro = ler_registro(pasta)
    agora = datetime.now().isoformat(timespec="seconds")
    novos = []
    for item in lancamentos:
        novos.append({"arquivo": arquivo, "materia_tec": item["materia_tec"], "meta": item.get("meta"),
                      "questoes": int(item["questoes"]), "acertos": int(item["acertos"]), "lancado_em": agora})
    registro.extend(novos)
    p.write_text(json.dumps({"lancamentos": registro}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"registrados": len(novos), "arquivo_registro": str(p)}


ROTEIRO = """Lançar o desempenho do TecConcursos nas Metas Diárias da mentoria.

1. Abra a página de metas da mentoria no navegador do usuário ({url}) e leia o título de cada meta
   de HOJE que ainda NÃO está concluída (ex.: "Simulado de Informática"). Não clique em nada ainda.
2. Chame `preparar_lancamentos_mentoria` com esses títulos.
3. Mostre ao usuário uma tabela: meta → matéria do TecConcursos → questões feitas → corretas, mais os
   ignorados, as matérias sem meta hoje e os avisos. Peça confirmação explícita. Sem um "sim", pare.
4. Para cada item aprovado, na página: marque "Meta concluída" daquela meta; na janela
   "Exercitando os Conhecimentos", preencha "Questões feitas" e "Questões corretas" com os valores
   aprovados e clique em Confirmar. Não lance metas fora da lista nem altere valores.
   Se a janela não abrir ou pedir outra coisa, pare e pergunte.
5. Chame `registrar_lancamentos_mentoria` só com os itens efetivamente salvos.
6. Diga ao usuário o que foi lançado e o que ficou de fora.
"""
