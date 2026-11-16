"""Planilhas oficiais de Estatísticas: layout copiado do export real, conteúdo inventado."""

import json
import os
from pathlib import Path

from openpyxl import Workbook

from tecconcursos_mcp import analysis
from tecconcursos_mcp.cli import importar
from tecconcursos_mcp.painel import gerar_painel
from tecconcursos_mcp.parsers import carregar_pasta
from tecconcursos_mcp.parsers.estatisticas import ler_snapshot_xlsx

CAB_DESEMPENHO = ["Hierarquia", "índice", "Questões Resolvidas", "Acertos (%)",
                  "Quantidade de acertos", "Erros (%)", "Quantidade de erros", "Peso"]
CAB_ATIVIDADES = ["Hierarquia", "Índice", "Questões Resolvidas"]


def _xlsx(caminho: Path, aba: str, cab: list, linhas: list, dimensao_errada: bool = False) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = aba
    ws.append(cab)
    for l in linhas:
        ws.append(l)
    wb.save(caminho)
    if dimensao_errada:  # o export real de Atividades declara <dimension ref="A1:H1"/>
        import zipfile
        tmp = caminho.with_suffix(".tmp")
        with zipfile.ZipFile(caminho) as zi, zipfile.ZipFile(tmp, "w") as zo:
            for item in zi.infolist():
                dados = zi.read(item.filename)
                if item.filename.startswith("xl/worksheets/sheet"):
                    import re
                    dados = re.sub(rb'<dimension ref="[^"]+"/>', b'<dimension ref="A1:H1"/>', dados)
                zo.writestr(item, dados)
        tmp.replace(caminho)
    return caminho


def desempenho(caminho: Path, alfa=(10, 4), beta=(6, 5)) -> Path:
    (ra, aa), (rb, ab) = alfa, beta
    return _xlsx(caminho, "Desempenho", CAB_DESEMPENHO, [
        [None, "Matéria Alfa", ra, 0, aa, 0, ra - aa, 1],
        ["01", "Tópico Um", 6, 0, 1, 0, 5, 1],
        ["01.01", "Subtópico Um-A", 4, 0, 0, 0, 4, 1],
        ["01.02", "Subtópico Um-B", 2, 0, 1, 0, 1, 1],
        ["02", "Tópico Dois", ra - 6, 0, aa - 1, 0, ra - 6 - aa + 1, 1],
        [None, "Matéria Beta", rb, 0, ab, 0, rb - ab, 1],
        ["01", "Tópico Três", rb, 0, ab, 0, rb - ab, 1],
    ])


def test_le_desempenho_com_hierarquia(tmp_path: Path):
    snap = ler_snapshot_xlsx(desempenho(tmp_path / "desempenho_2026-11-10.xlsx"))
    assert snap.tipo == "desempenho" and snap.data == "2026-11-10"
    assert [m.nome for m in snap.materias()] == ["Matéria Alfa", "Matéria Beta"]
    sub = next(l for l in snap.linhas if l.hierarquia == "01.02")
    assert sub.materia == "Matéria Alfa" and sub.caminho == ["Tópico Um", "Subtópico Um-B"]
    assert sub.nivel == 2 and sub.acertos == 1 and sub.erros == 1 and sub.taxa_acerto == 0.5


def test_le_atividades_com_dimensao_errada(tmp_path: Path):
    p = _xlsx(tmp_path / "x.xlsx", "Atividades", CAB_ATIVIDADES,
              [[None, "Matéria Alfa", 7.0], ["01", "Tópico Um", 7.0]], dimensao_errada=True)
    snap = ler_snapshot_xlsx(p)
    assert snap.tipo == "atividades" and len(snap.linhas) == 2
    assert snap.linhas[0].resolvidas == 7 and snap.linhas[0].acertos is None


def test_periodo_no_nome(tmp_path: Path):
    snap = ler_snapshot_xlsx(desempenho(tmp_path / "desempenho_2026-11-01_a_2026-11-07.xlsx"))
    assert snap.periodo_inicio == "2026-11-01" and snap.data == "2026-11-07"


def test_planilha_oficial_nao_vira_questao(tmp_path: Path):
    desempenho(tmp_path / "desempenho_2026-11-10.xlsx")
    bib = carregar_pasta(tmp_path)
    assert bib.questoes == [] and len(bib.snapshots) == 1
    assert bib.arquivos[0].snapshot == "desempenho"


def test_assuntos_fracos_e_progresso(tmp_path: Path):
    desempenho(tmp_path / "desempenho_2026-11-01.xlsx", alfa=(10, 4), beta=(6, 5))
    desempenho(tmp_path / "desempenho_2026-11-08.xlsx", alfa=(10, 5), beta=(6, 3))
    bib = carregar_pasta(tmp_path)
    fracos = analysis.desempenho_assuntos(bib.ultimo_snapshot(), nivel=None, min_questoes=2)
    assert fracos[0]["assunto"] == "Subtópico Um-A" and fracos[0]["taxa_acerto"] == 0.0

    prog = analysis.progresso(bib.snapshots)
    assert [p["data"] for p in prog["geral"]] == ["2026-11-01", "2026-11-08"]
    assert prog["materias"]["Matéria Alfa"]["variacao"]["diferenca_pontos"] == 10.0
    assert prog["materias"]["Matéria Beta"]["variacao"]["diferenca_pontos"] == -33.3
    assert analysis.progresso(bib.snapshots, materia="beta")["materias"].keys() == {"Matéria Beta"}


def test_importar_renomeia_e_nao_duplica(tmp_path: Path):
    downloads, exports = tmp_path / "dl", tmp_path / "exp"
    downloads.mkdir()
    p = desempenho(downloads / "2f0864ba-uuid.xlsx")
    os.utime(p, (1794700000, 1794700000))  # 2026-11-15 (UTC)
    (downloads / "outra.xlsx").write_bytes(b"nao e planilha")
    _xlsx(downloads / "qualquer.xlsx", "Plan1", ["Nome", "Valor"], [["a", 1]])

    res = importar(downloads, exports)
    assert [(r[0].name, r[2]) for r in res] == [("2f0864ba-uuid.xlsx", "importada")]
    assert res[0][1].name.startswith("desempenho_2026-11-1")
    assert importar(downloads, exports)[0][2] == "já importada"
    assert len(list(exports.glob("*.xlsx"))) == 1


def test_painel_html(tmp_path: Path):
    desempenho(tmp_path / "desempenho_2026-11-01.xlsx")
    desempenho(tmp_path / "desempenho_2026-11-08.xlsx", alfa=(10, 5))
    html = gerar_painel(carregar_pasta(tmp_path).snapshots)
    assert "<title>Meu progresso TecConcursos</title>" in html
    assert "Matéria Alfa" in html and "Subtópico Um-A" in html and "<svg" in html


def test_ferramentas_mcp(tmp_path: Path, monkeypatch):
    from .test_analysis_e_server import _chamar

    desempenho(tmp_path / "desempenho_2026-11-01.xlsx")
    monkeypatch.setenv("TEC_EXPORTS_DIR", str(tmp_path))
    r = _chamar("resumo_geral")["estatisticas_tec"]
    assert r["resolvidas"] == 16 and r["taxa_acerto"] == round(9 / 16, 4)
    linhas = _chamar("desempenho_assuntos", {"nivel": 0, "ordenar": "fortes"})["linhas"]
    assert [l["materia"] for l in linhas] == ["Matéria Beta", "Matéria Alfa"]
    assert _chamar("progresso")["snapshots"] == 1
    assert "desempenho_assuntos" in _chamar("desempenho")["erro"]
