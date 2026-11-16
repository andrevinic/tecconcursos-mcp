import json
from pathlib import Path

import pytest

from tecconcursos_mcp import analysis
from tecconcursos_mcp.painel import gerar_painel
from tecconcursos_mcp.parsers import carregar_pasta, qconcursos

from .test_estatisticas import desempenho


def _dias(pasta: Path):
    qconcursos.salvar(pasta, "2026-11-08", [{"nome": "Disciplina A", "certas": 6, "erradas": 4},
                                            {"nome": "Disciplina B", "certas": 1, "erradas": 1}],
                      [{"nome": "Assunto X", "certas": 0, "erradas": 3}])
    qconcursos.salvar(pasta, "2026-11-09", [{"nome": "Disciplina A", "certas": 4, "erradas": 1}],
                      [{"nome": "Assunto X", "certas": 1, "erradas": 1}])


def test_salvar_e_ler(tmp_path: Path):
    _dias(tmp_path)
    bib = carregar_pasta(tmp_path)
    assert bib.questoes == [] and len(bib.snapshots) == 2
    s = bib.snapshots[0]
    assert s.fonte == "qconcursos" and s.data == s.periodo_inicio == "2026-11-08"
    assert [m.nome for m in s.materias()] == ["Disciplina A", "Disciplina B"]
    assert bib.ultimo_snapshot() is None  # TEC continua separado


def test_salvar_valida(tmp_path: Path):
    with pytest.raises(ValueError):
        qconcursos.salvar(tmp_path, "2026-11-08", [{"nome": "", "certas": 1, "erradas": 0}])
    with pytest.raises(ValueError):
        qconcursos.salvar(tmp_path, "2999-01-01", [])
    # mesmo dia sobrescreve
    qconcursos.salvar(tmp_path, "2026-11-08", [{"nome": "A", "certas": 1, "erradas": 0}])
    qconcursos.salvar(tmp_path, "2026-11-08", [{"nome": "A", "certas": 2, "erradas": 0}])
    assert len(list(tmp_path.glob("qconcursos_*.json"))) == 1


def test_totais_e_progresso_por_fonte(tmp_path: Path):
    _dias(tmp_path)
    desempenho(tmp_path / "desempenho_2026-11-08.xlsx")
    bib = carregar_pasta(tmp_path)
    tot = {t["materia"]: t for t in analysis.totais(bib.snapshots)}
    assert tot["Disciplina A"]["resolvidas"] == 15 and tot["Disciplina A"]["acertos"] == 10
    assuntos = analysis.totais(bib.snapshots, nivel=1)
    assert assuntos == [{"assunto": "Assunto X", "resolvidas": 5, "acertos": 1, "erros": 4,
                         "taxa_acerto": 0.2, "indice_confianca": assuntos[0]["indice_confianca"]}]
    pq = analysis.progresso(bib.snapshots, fonte="qconcursos")
    assert [p["resolvidas"] for p in pq["geral"]] == [12, 5]
    assert set(analysis.progresso(bib.snapshots)["materias"]) == {"Matéria Alfa", "Matéria Beta"}


def test_painel_com_duas_fontes(tmp_path: Path):
    _dias(tmp_path)
    desempenho(tmp_path / "desempenho_2026-11-08.xlsx")
    html = gerar_painel(carregar_pasta(tmp_path).snapshots)
    assert 'id="tec"' in html and 'id="qconcursos"' in html and "Assunto X" in html
    assert html.count("<svg") == 4


def test_ferramentas_e_prompt(tmp_path: Path, monkeypatch):
    from .test_analysis_e_server import _chamar

    monkeypatch.setenv("TEC_EXPORTS_DIR", str(tmp_path))
    r = _chamar("salvar_estatisticas_qconcursos", {
        "data": "2026-11-08", "disciplinas": [{"nome": "Disciplina A", "certas": 3, "erradas": 1}]})
    assert r["questoes"] == 4 and Path(r["arquivo"]).exists()
    assert "erro" in _chamar("salvar_estatisticas_qconcursos", {"data": "ontem", "disciplinas": []})
    resumo = _chamar("resumo_geral")["qconcursos"]
    assert resumo["dias_salvos"] == 1 and resumo["taxa_acerto"] == 0.75
    assert _chamar("progresso", {"fonte": "qconcursos"})["snapshots"] == 1
    linhas = _chamar("desempenho_assuntos", {"fonte": "qconcursos", "nivel": 0})["linhas"]
    assert linhas[0]["materia"] == "Disciplina A"

    import asyncio
    from mcp.client.client import Client
    from tecconcursos_mcp.server import mcp

    async def run():
        async with Client(mcp) as c:
            return await c.get_prompt("coletar_qconcursos", {})
    texto = asyncio.run(run()).messages[0].content.text
    assert "NUNCA clique em \"zerar\"" in texto and "querySelectorAll" in texto
