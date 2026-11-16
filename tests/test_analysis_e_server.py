import asyncio
import json
from pathlib import Path

from mcp.client.client import Client

from tecconcursos_mcp import analysis
from tecconcursos_mcp.parsers import carregar_pasta
from tecconcursos_mcp.server import mcp


def test_resumo_e_desempenho(pasta_exports: Path):
    qs = carregar_pasta(pasta_exports).questoes
    r = analysis.resumo_geral(qs)
    assert r["respondidas"] == 7 and r["acertos"] == 3 and r["erros"] == 4
    assert r["periodo"] == {"inicio": "2026-10-01", "fim": "2026-10-06"}

    por_materia = {l["materia"]: l for l in analysis.desempenho(qs, "materia")}
    assert por_materia["Direito Penal"]["taxa_acerto"] == round(1 / 3, 4)
    assert por_materia["Física"]["acertos"] == 2

    # filtro sem acento e parcial
    assuntos = analysis.desempenho(qs, "assunto", materia="fisica")
    assert {l["assunto"] for l in assuntos} == {"Cinemática", "Dinâmica"}


def test_pontos_fracos_e_erradas(pasta_exports: Path):
    qs = carregar_pasta(pasta_exports).questoes
    fracos = analysis.pontos_fracos(qs, "assunto", min_questoes=1)
    assert fracos[0]["taxa_acerto"] == 0.0
    assert all("indice_confianca" in l for l in fracos)

    erradas = analysis.questoes_erradas(qs, materia="penal")
    assert [q.id for q in erradas] == ["900003", "900002"]  # mais recente primeiro


def test_buscar(pasta_exports: Path):
    qs = carregar_pasta(pasta_exports).questoes
    assert [q.id for q in analysis.buscar(qs, "MOLS")] == ["900007"]
    assert analysis.buscar(qs, "") == []


def test_wilson_penaliza_amostra_pequena():
    assert analysis._wilson_inferior(1, 1) < analysis._wilson_inferior(95, 100)


def _chamar(nome: str, args: dict | None = None) -> dict:
    async def run():
        async with Client(mcp) as c:
            res = await c.call_tool(nome, args or {})
            return json.loads(res.content[0].text)
    return asyncio.run(run())


def test_servidor_ponta_a_ponta(pasta_exports: Path, monkeypatch):
    monkeypatch.setenv("TEC_EXPORTS_DIR", str(pasta_exports))
    assert _chamar("resumo_geral")["exports_por_questao"]["respondidas"] == 7
    assert _chamar("listar_exports")["total_questoes"] == 7
    grupos = _chamar("desempenho", {"agrupar_por": "banca"})["grupos"]
    assert {g["banca"] for g in grupos} == {"Banca Alfa", "Banca Beta"}
    assert _chamar("desempenho", {"agrupar_por": "xyz"})["erro"]
    assert _chamar("questoes_erradas", {"banca": "beta"})["total"] == 2
    assert _chamar("buscar_questao", {"termo": "mols"})["total"] == 1


def test_servidor_pasta_inexistente(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TEC_EXPORTS_DIR", str(tmp_path / "nao-existe"))
    assert "Pasta não encontrada" in _chamar("resumo_geral")["erro"]
