"""Leitura de exports em planilha (CSV / XLSX) e JSON.

Os nomes de coluna variam conforme o export, então cada campo aceita vários
apelidos (comparados sem acento e sem diferenciar maiúsculas).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from ..models import Questao, normalizar

APELIDOS: dict[str, list[str]] = {
    "id": ["id", "codigo", "cod", "codigo da questao", "id questao", "questao", "numero"],
    "materia": ["materia", "disciplina", "materia/disciplina"],
    "assunto": ["assunto", "assuntos", "topico", "tema"],
    "banca": ["banca", "organizadora", "banca organizadora"],
    "orgao": ["orgao", "instituicao", "entidade"],
    "cargo": ["cargo", "carreira", "prova"],
    "ano": ["ano", "ano da prova"],
    "enunciado": ["enunciado", "texto", "questao texto", "pergunta"],
    "gabarito": ["gabarito", "resposta correta", "alternativa correta", "correta"],
    "resposta": ["resposta", "sua resposta", "resposta marcada", "marcada", "resposta do aluno"],
    "acertou": ["acertou", "resultado", "situacao", "status", "acerto"],
    "data": ["data", "data da resolucao", "resolvida em", "data resolucao"],
}

_INDICE = {normalizar(a): campo for campo, lista in APELIDOS.items() for a in lista}

VERDADEIRO = {"certo", "acertou", "acerto", "correta", "correto", "sim", "s", "true", "1", "v"}
FALSO = {"errado", "errou", "erro", "incorreta", "incorreto", "nao", "n", "false", "0", "f"}


def _bool(valor: Any) -> bool | None:
    if isinstance(valor, bool):
        return valor
    v = normalizar(str(valor)) if valor is not None else ""
    if v in VERDADEIRO:
        return True
    if v in FALSO:
        return False
    return None


def _ano(valor: Any) -> int | None:
    try:
        n = int(str(valor).strip()[:4])
        return n if 1900 < n < 2100 else None
    except (TypeError, ValueError):
        return None


def linha_para_questao(linha: dict[str, Any], arquivo: str) -> Questao | None:
    dados: dict[str, Any] = {}
    for coluna, valor in linha.items():
        campo = _INDICE.get(normalizar(coluna or ""))
        if campo and valor not in (None, "") and campo not in dados:
            dados[campo] = valor
    if not dados:
        return None
    if "acertou" in dados:
        dados["acertou"] = _bool(dados["acertou"])
    if "ano" in dados:
        dados["ano"] = _ano(dados["ano"])
    if "alternativas" in linha and isinstance(linha["alternativas"], list):
        dados["alternativas"] = [str(a) for a in linha["alternativas"]]
    for campo in ("id", "materia", "assunto", "banca", "orgao", "cargo",
                  "enunciado", "gabarito", "resposta", "data"):
        if campo in dados and dados[campo] is not None:
            dados[campo] = str(dados[campo]).strip()
    return Questao(arquivo=arquivo, **dados)


def _linhas_para_questoes(linhas: Iterable[dict[str, Any]], arquivo: str) -> list[Questao]:
    return [q for linha in linhas if (q := linha_para_questao(linha, arquivo))]


def ler_csv(caminho: Path) -> list[Questao]:
    bruto = caminho.read_bytes()
    for codificacao in ("utf-8-sig", "latin-1"):
        try:
            texto = bruto.decode(codificacao)
            break
        except UnicodeDecodeError:
            continue
    try:
        dialeto = csv.Sniffer().sniff(texto[:4096], delimiters=",;\t")
    except csv.Error:
        dialeto = csv.excel
    return _linhas_para_questoes(csv.DictReader(texto.splitlines(), dialect=dialeto), caminho.name)


def ler_xlsx(caminho: Path) -> list[Questao]:
    from openpyxl import load_workbook

    wb = load_workbook(caminho, read_only=True, data_only=True)
    questoes: list[Questao] = []
    for ws in wb.worksheets:
        linhas = ws.iter_rows(values_only=True)
        cabecalho = next(linhas, None)
        if not cabecalho:
            continue
        nomes = [str(c) if c is not None else "" for c in cabecalho]
        questoes += _linhas_para_questoes((dict(zip(nomes, l)) for l in linhas), caminho.name)
    wb.close()
    return questoes


def ler_json(caminho: Path) -> list[Questao]:
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    if isinstance(dados, dict):
        # aceita {"questoes": [...]} ou qualquer chave que contenha a lista
        dados = next((v for v in dados.values() if isinstance(v, list)), [dados])
    return _linhas_para_questoes((d for d in dados if isinstance(d, dict)), caminho.name)
