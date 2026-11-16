from pathlib import Path

from openpyxl import Workbook

from tecconcursos_mcp.parsers import carregar_pasta
from tecconcursos_mcp.parsers.pdf import ler_pdf, parse_texto
from tecconcursos_mcp.parsers.tabular import ler_csv, ler_xlsx

from .conftest import PDF_TEXTO


def test_csv_ponto_e_virgula_e_acerto_deduzido(pasta_exports: Path):
    qs = ler_csv(pasta_exports / "estatisticas.csv")
    assert len(qs) == 6
    q1, q2 = qs[0], qs[1]
    assert q1.materia == "Direito Penal" and q1.orgao == "Órgão X" and q1.ano == 2021
    assert q1.acertou is True   # gabarito C == resposta C
    assert q2.acertou is False  # gabarito E != resposta C


def test_csv_latin1(tmp_path: Path):
    p = tmp_path / "l1.csv"
    p.write_bytes("Matéria,Resultado\nPortuguês,Certo\n".encode("latin-1"))
    [q] = ler_csv(p)
    assert q.materia == "Português" and q.acertou is True


def test_xlsx(tmp_path: Path):
    wb = Workbook()
    ws = wb.active
    ws.append(["ID", "Disciplina", "Situação"])
    ws.append([123, "Contabilidade", "Errou"])
    p = tmp_path / "x.xlsx"
    wb.save(p)
    [q] = ler_xlsx(p)
    assert q.id == "123" and q.materia == "Contabilidade" and q.acertou is False


def test_carregar_pasta_deduplica_e_ignora_outros(pasta_exports: Path):
    bib = carregar_pasta(pasta_exports)
    assert {a.arquivo for a in bib.arquivos} == {"estatisticas.csv", "extra.json"}
    assert len(bib.questoes) == 7
    q = next(q for q in bib.questoes if q.id == "900001")
    assert q.acertou is True  # a versão respondida (CSV) venceu a do JSON


def test_arquivo_corrompido_nao_derruba(pasta_exports: Path):
    (pasta_exports / "ruim.xlsx").write_bytes(b"nao e xlsx")
    bib = carregar_pasta(pasta_exports)
    ruim = next(a for a in bib.arquivos if a.arquivo == "ruim.xlsx")
    assert ruim.erro and len(bib.questoes) == 7


def test_pdf_texto():
    q1, q2 = parse_texto(PDF_TEXTO, "caderno.pdf")
    assert q1.id == "900101" and q1.banca == "Banca Alfa" and q1.orgao == "Órgão X"
    assert q1.cargo == "Cargo Y" and q1.ano == 2019
    assert q1.materia == "Informática" and q1.assunto == "Redes"
    assert q1.alternativas == ["A) Opção um", "B) Opção dois", "C) Opção três"]
    assert q1.gabarito == "B"
    assert q1.enunciado == "Enunciado inventado sobre protocolos de rede."
    assert q2.gabarito == "C" and q2.assunto == "Segurança" and q2.alternativas == []


def test_pdf_real(tmp_path: Path):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    p = tmp_path / "caderno.pdf"
    c = canvas.Canvas(str(p), pagesize=A4)
    y = 800
    for linha in PDF_TEXTO.splitlines():
        c.drawString(40, y, linha)
        y -= 16
    c.save()
    qs = ler_pdf(p)
    assert [q.id for q in qs] == ["900101", "900102"]
    assert qs[0].gabarito == "B"
