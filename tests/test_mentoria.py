import json
from datetime import date
from pathlib import Path

from tecconcursos_mcp import mentoria
from tecconcursos_mcp.parsers import carregar_pasta

from .test_estatisticas import desempenho

TEC = ["Língua Portuguesa (Português)", "Direito Constitucional (CF/1988 e Doutrina)",
       "Noções de Informática", "Direito Processual Penal"]


def test_casar_por_nome_base():
    assert mentoria.casar("Simulado de Língua Portuguesa (VTM)", TEC, {}) == TEC[0]
    assert mentoria.casar("Simulado de Direito Constitucional (VTM)", TEC, {}) == TEC[1]
    assert mentoria.casar("Simulado de Informática", TEC, {}) == TEC[2]
    assert mentoria.casar("Simulado de Direito Penal (VTM)", TEC, {}) is None  # não confunde com processual
    assert mentoria.casar("Simulado de Direito Penal (VTM)", TEC, {"direito penal": "Direito Processual Penal"}) == TEC[3]


def test_preparar_e_registrar(tmp_path: Path):
    desempenho(tmp_path / "desempenho_2026-11-16.xlsx")  # Matéria Alfa 10/4, Matéria Beta 6/5
    (tmp_path / mentoria.ARQ_MAPA).write_text(json.dumps({"materias": {"Revisão X": "Matéria Beta"}}), encoding="utf-8")
    snap = carregar_pasta(tmp_path).ultimo_snapshot()

    r = mentoria.preparar(snap, ["Simulado de Matéria Alfa (VTM)", "Revisão X", "Simulado de Gama"],
                          tmp_path, hoje=date(2026, 11, 16))
    assert r["lancar"] == [
        {"meta": "Simulado de Matéria Alfa (VTM)", "materia_tec": "Matéria Alfa", "questoes": 10, "acertos": 4},
        {"meta": "Revisão X", "materia_tec": "Matéria Beta", "questoes": 6, "acertos": 5},
    ]
    assert [i["meta"] for i in r["ignorados"]] == ["Simulado de Gama"]
    assert len(r["avisos"]) == 1  # planilha é de hoje: só o aviso do período

    mentoria.registrar(tmp_path, r["planilha"], r["lancar"][:1])
    r2 = mentoria.preparar(snap, ["Simulado de Matéria Alfa (VTM)", "Revisão X"], tmp_path, hoje=date(2026, 11, 16))
    assert [i["materia_tec"] for i in r2["lancar"]] == ["Matéria Beta"]
    assert "já foi lançada" in r2["ignorados"][0]["motivo"]


def test_ferramentas_e_prompt(tmp_path: Path, monkeypatch):
    from .test_analysis_e_server import _chamar

    desempenho(tmp_path / "desempenho_2026-11-16.xlsx")
    monkeypatch.setenv("TEC_EXPORTS_DIR", str(tmp_path))
    r = _chamar("preparar_lancamentos_mentoria", {"metas": ["Simulado de Matéria Beta"]})
    assert r["lancar"][0]["questoes"] == 6
    assert _chamar("registrar_lancamentos_mentoria", {"planilha": "nao-existe.xlsx", "lancamentos": []})["erro"]
    ok = _chamar("registrar_lancamentos_mentoria", {"planilha": r["planilha"], "lancamentos": r["lancar"]})
    assert ok["registrados"] == 1
    assert _chamar("preparar_lancamentos_mentoria", {"metas": ["Simulado de Matéria Beta"]})["lancar"] == []

    import asyncio
    from mcp.client.client import Client
    from tecconcursos_mcp.server import mcp

    async def run():
        async with Client(mcp) as c:
            return await c.get_prompt("lancar_metas_mentoria", {})
    texto = asyncio.run(run()).messages[0].content.text
    assert "preparar_lancamentos_mentoria" in texto and "confirmação" in texto
