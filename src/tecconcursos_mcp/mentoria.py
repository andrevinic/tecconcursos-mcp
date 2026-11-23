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

from . import mapa_assuntos
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


def ler_assuntos_extra(pasta: Path) -> dict[str, list[str]]:
    p = pasta / ARQ_MAPA
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8")).get("assuntos") or {}


def _folhas(snap: Snapshot, materia: str):
    linhas = [l for l in snap.linhas if l.materia == materia and l.nivel >= 1]
    hs = [l.hierarquia for l in linhas]
    return [l for l in linhas if not any(h != l.hierarquia and h.startswith(l.hierarquia + ".") for h in hs)]


def por_assunto(snap: Snapshot | None, materia: str, pasta: Path) -> dict[str, Any]:
    """Questões de UMA matéria da planilha agrupadas pelos assuntos da mentoria.

    Use para lançar na página "Lançamentos de Questões" da mentoria (disciplina + assunto + data),
    em vez de jogar tudo num assunto só.
    """
    if snap is None or not snap.tem_acertos:
        return {"erro": "Nenhuma planilha de Desempenho na pasta."}
    mats = [l.materia for l in snap.materias()]
    tec = next((m for m in mats if normalizar(m) == normalizar(materia)), None) or casar(materia, mats, {})
    if tec is None:
        return {"erro": f"Matéria '{materia}' não está na planilha. Matérias: {', '.join(mats)}"}
    extra = ler_assuntos_extra(pasta)
    grupos: dict[str, dict[str, Any]] = {}
    for f in _folhas(snap, tec):
        alvo = mapa_assuntos.assunto_tutory(tec, f.caminho or [f.nome], extra)
        g = grupos.setdefault(alvo, {"assunto_mentoria": alvo, "questoes": 0, "acertos": 0, "assuntos_tec": []})
        g["questoes"] += f.resolvidas
        g["acertos"] += f.acertos or 0
        g["assuntos_tec"].append(f"{f.nome} ({f.acertos or 0}/{f.resolvidas})")
    linha = next(l for l in snap.materias() if l.materia == tec)
    soma = sum(g["questoes"] for g in grupos.values())
    avisos = []
    if soma != linha.resolvidas:
        avisos.append(f"A soma dos assuntos ({soma}) difere do total da matéria ({linha.resolvidas}): "
                      "alguma questão aparece em mais de um assunto. Ajuste o grupo 'Assunto Livre' para fechar.")
    lista = sorted(grupos.values(), key=lambda g: (g["assunto_mentoria"] == mapa_assuntos.ASSUNTO_LIVRE,
                                                   -g["questoes"]))
    return {"planilha": snap.arquivo, "materia_tec": tec, "total": {"questoes": linha.resolvidas,
            "acertos": linha.acertos}, "lancar": lista, "avisos": avisos}


# Questões por minuto de meta, por modalidade (itens Certo/Errado levam ~1,5 a 2 min com correção).
_RITMO = {"exercicio": 2.0, "simulado": 2.0, "revisao": 3.0, "estudo": 6.0}


def caderno_da_semana(metas: list[dict[str, Any]], pasta: Path) -> dict[str, Any]:
    """Plano de caderno no TecConcursos a partir das metas da semana na mentoria.

    ``metas``: [{"data", "disciplina", "assunto", "modalidade", "minutos"}], lidas do
    "Resumo da Semana". Devolve, por meta, os assuntos a marcar no filtro do TEC e quantas questões
    pegar; e um resumo por disciplina para montar um caderno só (ou um por dia).
    """
    extra = ler_assuntos_extra(pasta)
    itens, sem_mapa = [], []
    por_disc: dict[str, dict[str, Any]] = {}
    for m in metas:
        disc, assunto = m.get("disciplina", ""), m.get("assunto", "")
        if normalizar(disc).startswith(("revisao geral", "simulado quinzenal")) or not assunto:
            continue
        modal = normalizar(m.get("modalidade", ""))
        ritmo = next((v for k, v in _RITMO.items() if k in modal), 2.5)
        n = max(5, round(int(m.get("minutos") or 0) / ritmo))
        termos = [] if normalizar(assunto) == normalizar(mapa_assuntos.ASSUNTO_LIVRE) else \
            mapa_assuntos.termos_tec(disc, assunto, extra)
        item = {"data": m.get("data"), "disciplina": disc, "assunto_mentoria": assunto,
                "modalidade": m.get("modalidade"), "questoes_sugeridas": n, "assuntos_tec": termos}
        if not termos and normalizar(assunto) != normalizar(mapa_assuntos.ASSUNTO_LIVRE):
            sem_mapa.append(f"{disc} · {assunto}")
        itens.append(item)
        d = por_disc.setdefault(nome_base(disc), {"disciplina": disc, "questoes": 0, "assuntos_tec": []})
        d["questoes"] += n
        d["assuntos_tec"] += [t for t in termos if t not in d["assuntos_tec"]]
    avisos = []
    if sem_mapa:
        avisos.append("Sem correspondência no TEC (procure o assunto à mão ou acrescente em mentoria.json → "
                      "'assuntos'): " + "; ".join(sem_mapa))
    filtros = ler_filtros_caderno(pasta)
    if not filtros["cargos"] and not filtros["bancas"]:
        avisos.append("Sem 'cargos' nem 'bancas' em mentoria.json → 'caderno': o caderno trará questões de qualquer "
                      "cargo (inclusive Delegado). Liste os cargos-alvo (ex.: 'Perito Criminal', "
                      "'Policial Rodoviário Federal').")
    return {"metas": itens, "caderno": list(por_disc.values()), "filtros": filtros,
            "total_questoes": sum(d["questoes"] for d in por_disc.values()), "avisos": avisos}


def ler_filtros_caderno(pasta: Path) -> dict[str, Any]:
    """Filtros do caderno da semana em mentoria.json → "caderno".

    ``cargos``: trechos de cargo do TEC a incluir (ex.: "Perito Criminal" pega todos os estados), o jeito
    certo de evitar questões de Delegado; ``cargos_excluir``: trechos a tirar (ex.: "Federal", "Auxiliar");
    ``bancas`` e ``anos_recentes``: opcionais, restringem mais.
    """
    p = pasta / ARQ_MAPA
    cfg = json.loads(p.read_text(encoding="utf-8")).get("caderno", {}) if p.is_file() else {}
    return {"cargos": list(cfg.get("cargos") or []), "cargos_excluir": list(cfg.get("cargos_excluir") or []),
            "bancas": list(cfg.get("bancas") or []), "anos_recentes": cfg.get("anos_recentes"),
            "remover": list(cfg.get("remover") or ["resolvi", "anuladas", "desatualizadas"]),
            "pasta_tec": cfg.get("pasta_tec")}


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


ROTEIRO = """Lançar o desempenho do TecConcursos na mentoria (Tutory), por assunto e na data certa.

Antes: se a página pedir login, pare e peça ao usuário para entrar (nunca digite a senha).

1. Números do dia. Use a planilha de Desempenho importada OU, para um dia específico, a página do TEC
   Estatísticas → Desempenho com o período = esse dia (abra cada matéria para ver os assuntos).
   O período da planilha não vem no arquivo: confira que cobre só o que ainda não foi lançado.
2. Leia as metas de HOJE na página de metas ({url}) e chame `preparar_lancamentos_mentoria` com os
   títulos (meta → matéria do TEC). Para cada matéria, chame `preparar_lancamentos_por_assunto`
   (assuntos do TEC → assuntos da mentoria). Mostre as tabelas ao usuário e peça confirmação
   explícita. Sem um "sim", pare.
3. Questões: na página "Lançamentos de Questões" ({url_lancamentos}) cadastre cada linha aprovada
   (disciplina, assunto, DATA do estudo, feitas, corretas). Depois de cada cadastro a página precisa ser
   recarregada. Confira a soma por disciplina na tabela "Suas Questões" no fim.
   Cuidado: a lixeira apaga TODAS as linhas idênticas (mesma data, assunto e números); nunca deixe
   duplicatas para apagar uma só.
4. Tempo: na meta do dia correspondente (página de metas, {url}), "Opções de Cronômetro" →
   "Lançamento Manual" (selects de horas/minutos/segundos). Se não houver meta daquela matéria hoje,
   use "Estudou algo fora do planejado hoje? Informe aqui" (cai no dia atual do plano) e lance o tempo
   no cartão criado. O cronômetro dos cadernos do TEC pode ter ficado ligado (ex.: 10h): não use um
   tempo absurdo; pergunte ou estime pelo ritmo da pessoa e diga que é estimativa.
5. Conclua a meta marcando "Meta concluída". Se as questões já foram lançadas no passo 3, feche a
   janela "Exercitando os Conhecimentos" no X e responda "Sim" para não contar em dobro.
6. Se o plano estiver parado num dia antigo com meta especial não feita (ex.: simulado), não marque
   como concluída: use "Replanejar atrasos" (o assistente pergunta "posso prosseguir?" → sim).
7. Chame `registrar_lancamentos_mentoria` com o que foi salvo e diga ao usuário o que entrou,
   o que ficou de fora e o que foi estimado.
"""

ROTEIRO_CADERNO = """Montar no TecConcursos o caderno de questões da semana a partir do plano da mentoria.

1. Abra o "Resumo da Semana" da mentoria ({url_semana}) e leia, para cada dia, as metas:
   disciplina, assunto, modalidade (Estudo, Exercício, Revisão...) e minutos. Pule metas especiais
   (simulado quinzenal, revisão geral). Se pedir login, peça ao usuário para entrar.
2. Chame `planejar_caderno_semana` com essas metas. Mostre ao usuário: por disciplina, os assuntos do
   TEC e quantas questões; e as metas sem correspondência. Peça confirmação.
3. No TEC: Estudo → Filtrar questões. Selecione as matérias e, na árvore de assuntos, os assuntos
   listados (busque pelos trechos). Aplique os `filtros` devolvidos:
   - "Órgão e cargo": cada cargo cujo nome contém um trecho de `cargos` e nenhum de `cargos_excluir`.
     Cargos com áreas são pastas: abra e marque "Todo o conteúdo de ...". Clicar de novo num item
     já ativo o DESMARCA; confira "Filtros ativos" depois de cada clique.
   - `bancas` e `anos_recentes`, só se vierem preenchidos.
   - Opções: "Remover as que resolvi", anuladas e desatualizadas.
   Em "Editar quantidades", ponha o número de questões de cada matéria (ou o máximo disponível).
4. Crie UM caderno chamado "Semana AAAA-MM-DD · Tutory" (data da segunda-feira) na pasta de estudo
   da pessoa. Não apague nem altere cadernos existentes.
5. Diga ao usuário o nome, o link e quantas questões o caderno tem, e quais metas ficaram sem questões.
"""
