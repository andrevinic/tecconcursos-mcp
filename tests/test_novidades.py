"""Testes das novidades da 0.4: link do e-mail, importação sem duplicatas, assuntos da mentoria e caderno da semana.
Dados 100% inventados."""

from pathlib import Path

from tecconcursos_mcp import email_tec, mapa_assuntos, mentoria
from tecconcursos_mcp.cli import importar
from tecconcursos_mcp.parsers import carregar_pasta

from .test_estatisticas import desempenho

EMAIL = (b"Subject: =?UTF-8?Q?Sua_exporta=C3=A7=C3=A3o?=\r\nContent-Transfer-Encoding: quoted-printable\r\n\r\n"
         b'<a href=3D"https://tec-exemplo.s3.amazonaws.com/exports/123/abcd-ef.xlsx?AWSAccessKeyId=3DX&amp;Sig=\r\n'
         b'nature=3DY">Baixar planilha (.xlsx)</a> <img src=3D"https://cdn.exemplo.com/logo.png">')


def test_extrair_link_do_email():
    url = email_tec.extrair_link(EMAIL)
    assert url == "https://tec-exemplo.s3.amazonaws.com/exports/123/abcd-ef.xlsx?AWSAccessKeyId=X&Signature=Y"
    assert email_tec.nome_do_arquivo(url) == "abcd-ef.xlsx"
    assert email_tec.extrair_link(b"sem link nenhum") is None


def test_baixar_recusa_host_estranho(tmp_path: Path):
    try:
        email_tec.baixar("https://exemplo.com/exports/x.xlsx", tmp_path)
    except ValueError as e:
        assert "Link inesperado" in str(e)
    else:
        raise AssertionError("deveria recusar")


def test_importar_pula_mesmo_conteudo_com_arquivo_diferente(tmp_path: Path):
    origem, destino = tmp_path / "dl", tmp_path / "exports"
    origem.mkdir()
    desempenho(origem / "a.xlsx")
    desempenho(origem / "b.xlsx")  # mesmas células, outro arquivo (como dois exports do TEC)
    res = importar(origem, destino)
    assert sorted(m for _, _, m in res) == ["importada", "já importada"]


def test_assunto_tutory_mais_especifico():
    assert mapa_assuntos.assunto_tutory("Direito Penal", ["Lei Penal", "Aplicação da Lei Penal (arts. 1º a 12)",
                                        "Aplicação da Lei Penal no Tempo", "Conflito Aparente de Normas Penais"]) \
        == "Aplicação da lei penal"
    assert mapa_assuntos.assunto_tutory("Direito Penal", ["Teoria do Crime", "Ilicitude e suas Excludentes",
                                        "Legítima Defesa (art. 25 do CP)"]) == "Ilicitude e causas de exclusão"
    assert mapa_assuntos.assunto_tutory("Direito Penal", ["Dos Crimes contra a Pessoa", "Da Rixa"]) == "Assunto Livre"
    assert mapa_assuntos.assunto_tutory("Matéria Alfa", ["Tópico Um"], {"Assunto X": ["topico um"]}) == "Assunto X"


def test_por_assunto_soma_e_agrupa(tmp_path: Path):
    desempenho(tmp_path / "desempenho_2026-11-16.xlsx")  # Alfa: 01.01 4/0, 01.02 2/1, 02 4/3
    (tmp_path / mentoria.ARQ_MAPA).write_text('{"assuntos": {"Grupo Um": ["subtopico um"]}}', encoding="utf-8")
    snap = carregar_pasta(tmp_path).ultimo_snapshot()
    r = mentoria.por_assunto(snap, "matéria alfa", tmp_path)
    assert r["total"] == {"questoes": 10, "acertos": 4} and not r["avisos"]
    grupos = {g["assunto_mentoria"]: (g["questoes"], g["acertos"]) for g in r["lancar"]}
    assert grupos == {"Grupo Um": (6, 1), "Assunto Livre": (4, 3)}


def test_caderno_da_semana(tmp_path: Path):
    metas = [
        {"data": "2026-11-24", "disciplina": "Direito Penal (VTM)", "assunto": "Aplicação da lei penal",
         "modalidade": "Exercício", "minutos": 30},
        {"data": "2026-11-25", "disciplina": "Direito Processual Penal (VTM)",
         "assunto": "Inquérito policial: histórico; natureza", "modalidade": "Estudo", "minutos": 60},
        {"data": "2026-11-28", "disciplina": "Revisão Geral Semanal", "assunto": "", "minutos": 180},
        {"data": "2026-11-26", "disciplina": "Direito Penal (VTM)", "assunto": "Assunto inventado",
         "modalidade": "Revisão", "minutos": 30},
    ]
    r = mentoria.caderno_da_semana(metas, tmp_path)
    assert [m["questoes_sugeridas"] for m in r["metas"]] == [15, 10, 0]
    assert r["metas"][1]["assuntos_tec"] == ["inquerito policial"]
    assert "Assunto inventado" in r["avisos"][0]
    assert r["total_questoes"] == 25


def test_caderno_filtros_bancas(tmp_path: Path):
    (tmp_path / mentoria.ARQ_MAPA).write_text(
        '{"caderno": {"cargos": ["Perito Criminal"], "cargos_excluir": ["Federal"]}}', encoding="utf-8")
    r = mentoria.caderno_da_semana([], tmp_path)
    assert r["filtros"]["cargos"] == ["Perito Criminal"] and r["filtros"]["cargos_excluir"] == ["Federal"]
    assert not r["avisos"]
    assert "Delegado" in mentoria.caderno_da_semana([], tmp_path / "vazio")["avisos"][0]
