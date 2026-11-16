"""Estatísticas do QConcursos (Minhas Estatísticas → Disciplina / Assunto).

O QConcursos não tem export. O cliente MCP (ex.: Claude no navegador do usuário) lê a
tabela da página filtrada por **um dia** e chama a ferramenta
`salvar_estatisticas_qconcursos`, que grava ``qconcursos_AAAA-MM-DD.json``::

    {"fonte": "qconcursos", "data": "2026-11-08", "coletado_em": "...",
     "disciplinas": [{"nome": "Português", "certas": 13, "erradas": 8}],
     "assuntos":    [{"nome": "Interpretação de Textos", "certas": 9, "erradas": 6}]}

Um arquivo por dia: assim os dias nunca se sobrepõem e somar dá o total exato.
A página de Assuntos não diz a disciplina de cada assunto; eles ficam sob
``MATERIA_ASSUNTOS``.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from ..models import LinhaEstatistica, Snapshot

FONTE = "qconcursos"
MATERIA_ASSUNTOS = "Assuntos (QConcursos, sem disciplina)"


def eh_qconcursos(dados: Any) -> bool:
    return isinstance(dados, dict) and dados.get("fonte") == FONTE


def _linhas(itens: list[dict[str, Any]]) -> list[tuple[str, int, int]]:
    saida = []
    for i in itens or []:
        nome = str(i.get("nome", "")).strip()
        certas, erradas = int(i.get("certas", 0)), int(i.get("erradas", 0))
        if not nome or certas < 0 or erradas < 0:
            raise ValueError(f"linha inválida: {i!r}")
        saida.append((nome, certas, erradas))
    return saida


def para_snapshot(dados: dict[str, Any], arquivo: str) -> Snapshot:
    dia = date.fromisoformat(dados["data"]).isoformat()
    snap = Snapshot(arquivo=arquivo, tipo="desempenho", data=dia, periodo_inicio=dia, fonte=FONTE)
    for nome, c, e in _linhas(dados.get("disciplinas", [])):
        snap.linhas.append(LinhaEstatistica(materia=nome, nome=nome, resolvidas=c + e, acertos=c, erros=e))
    for k, (nome, c, e) in enumerate(_linhas(dados.get("assuntos", []))):
        snap.linhas.append(LinhaEstatistica(materia=MATERIA_ASSUNTOS, nome=nome, hierarquia=f"{k + 1:02d}",
                                            caminho=[nome], resolvidas=c + e, acertos=c, erros=e))
    return snap


def ler_qconcursos(caminho: Path) -> Snapshot | None:
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    return para_snapshot(dados, caminho.name) if eh_qconcursos(dados) else None


def salvar(pasta: Path, dia: str, disciplinas: list[dict[str, Any]],
           assuntos: list[dict[str, Any]] | None = None) -> Path:
    """Valida e grava (sobrescreve o mesmo dia, se já existir)."""
    d = date.fromisoformat(dia)
    if d > date.today():
        raise ValueError("data no futuro")
    dados = {
        "fonte": FONTE,
        "data": d.isoformat(),
        "coletado_em": datetime.now().isoformat(timespec="seconds"),
        "disciplinas": [{"nome": n, "certas": c, "erradas": e} for n, c, e in _linhas(disciplinas)],
        "assuntos": [{"nome": n, "certas": c, "erradas": e} for n, c, e in _linhas(assuntos or [])],
    }
    pasta.mkdir(parents=True, exist_ok=True)
    alvo = pasta / f"{FONTE}_{d.isoformat()}.json"
    alvo.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    return alvo


# Executado pelo cliente na página do QConcursos (só lê o DOM).
SCRIPT_LEITURA = r"""(() => {
  const n = s => parseInt(String(s).replace(/\D/g, '')) || 0;
  return [...document.querySelectorAll('main table tr')].map(r => [...r.cells])
    .filter(c => c.length >= 4 && /^\d+$/.test(c[1].textContent.trim()))
    .map(c => ({ nome: (c[0].querySelector('[title]')?.getAttribute('title') || c[0].getAttribute('title') || c[0].textContent).trim(),
                 certas: n(c[1].textContent), erradas: n(c[2].textContent) }));
})()"""

ROTEIRO = """Coletar as estatísticas do QConcursos (o site não tem export).

1. Chame `listar_exports` para ver o último dia já salvo (arquivos `qconcursos_AAAA-MM-DD.json`).
   Se não houver nenhum, descubra o primeiro dia com atividade abrindo
   https://www.qconcursos.com/usuario/estatisticas/disciplinas?gt=2000-01-01&lt=<hoje>.
2. Para cada dia D ainda não salvo, até hoje, no navegador do usuário (já logado):
   - abra https://www.qconcursos.com/usuario/estatisticas/disciplinas?gt=D&lt=D e rode o script abaixo;
   - abra https://www.qconcursos.com/usuario/estatisticas/assuntos?gt=D&lt=D e rode o mesmo script;
   - se a tabela de disciplinas vier vazia, pule o dia; senão chame
     `salvar_estatisticas_qconcursos(data=D, disciplinas=..., assuntos=...)`.
   Espere ~0,5 s entre páginas. O dia de hoje pode ser salvo de novo depois (sobrescreve).
3. NUNCA clique em "zerar" (apaga as estatísticas no site) nem em nada além de navegar e ler.
4. Mostre ao usuário o resumo: dias salvos, questões e acertos.

Script de leitura (só lê a tabela):
{script}
"""
