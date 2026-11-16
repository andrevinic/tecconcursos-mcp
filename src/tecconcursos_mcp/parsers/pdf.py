"""Leitura de cadernos exportados em PDF (EXPERIMENTAL).

O layout exato do PDF pode mudar; este parser usa heurísticas tolerantes:

* uma questão começa numa linha como ``1)``, ``1.``, ``Questão 1`` ou ``Q1``;
* metadados rotulados (``Banca:``, ``Órgão:``, ``Cargo:``, ``Ano:``,
  ``Matéria:``/``Disciplina:``, ``Assunto:``) são extraídos onde aparecerem;
* alternativas começam com ``a)``, ``(A)``, ``A -`` etc.;
* uma seção final ``Gabarito`` com pares ``1) C 2) E 3) A`` preenche o gabarito.

Se o seu PDF não for reconhecido, abra uma issue com um trecho *anonimizado*.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..models import Questao

_INICIO = re.compile(r"^\s*(?:quest[aã]o\s*|q)?(\d{1,4})\s*[).:\-–]\s+(.*)$", re.IGNORECASE)
_ALTERNATIVA = re.compile(r"^\s*\(?([A-Ea-e])\s*[).\-–]\s+(.+)$")
_GABARITO_TITULO = re.compile(r"^\s*gabaritos?\b", re.IGNORECASE)
_GABARITO_PAR = re.compile(
    r"(\d{1,4})\s*[).:\-–]?\s*(certo|errado|anulada|[A-E])\b", re.IGNORECASE
)

_ROTULOS = {
    "banca": r"banca",
    "orgao": r"[óo]rg[ãa]o",
    "cargo": r"cargo",
    "ano": r"ano",
    "materia": r"(?:mat[ée]ria|disciplina)",
    "assunto": r"assunto",
}
_PROX_ROTULO = "|".join(_ROTULOS.values())
_METADADO = {
    campo: re.compile(
        rf"\b{rotulo}\s*:\s*(.+?)(?=\s*(?:[-|/•]\s*)?\b(?:{_PROX_ROTULO})\s*:|$)",
        re.IGNORECASE,
    )
    for campo, rotulo in _ROTULOS.items()
}


def _gabarito(linhas: list[str]) -> dict[str, str]:
    texto = " ".join(linhas)
    return {num: resp.upper()[0] if resp.lower() in ("certo", "errado") else resp.upper()
            for num, resp in _GABARITO_PAR.findall(texto)}


def parse_texto(texto: str, arquivo: str = "") -> list[Questao]:
    linhas = [l.rstrip() for l in texto.splitlines()]

    # separa a seção de gabarito (a última que aparecer)
    corte = max((i for i, l in enumerate(linhas) if _GABARITO_TITULO.match(l)), default=None)
    gabarito = _gabarito(linhas[corte + 1:]) if corte is not None else {}
    corpo = linhas[:corte] if corte is not None else linhas

    blocos: list[tuple[str, list[str]]] = []
    esperado = 1
    for linha in corpo:
        m = _INICIO.match(linha)
        # só aceita a numeração sequencial, para não confundir com "1. Item" no enunciado
        if m and int(m.group(1)) == esperado:
            blocos.append((m.group(1), [m.group(2)]))
            esperado += 1
        elif blocos:
            blocos[-1][1].append(linha)

    questoes: list[Questao] = []
    for numero, conteudo in blocos:
        # código da questão (5+ dígitos) logo após a numeração, ex.: "1) 123456 ..."
        id_tec = None
        if (m := re.match(r"^#?(\d{5,})\b\s*(.*)$", conteudo[0])):
            id_tec, conteudo[0] = m.group(1), m.group(2)
        meta: dict[str, str] = {}
        enunciado: list[str] = []
        alternativas: list[str] = []
        for linha in conteudo:
            achou_meta = False
            for campo, rx in _METADADO.items():
                if campo not in meta and (m := rx.search(linha)):
                    meta[campo] = m.group(1).strip(" -|•")
                    achou_meta = True
            if achou_meta:
                continue
            if (m := _ALTERNATIVA.match(linha)):
                alternativas.append(f"{m.group(1).upper()}) {m.group(2).strip()}")
            elif alternativas and linha.strip():
                alternativas[-1] += " " + linha.strip()
            elif linha.strip():
                enunciado.append(linha.strip())

        ano = meta.get("ano")
        questoes.append(Questao(
            id=id_tec or f"{arquivo}#{numero}",
            materia=meta.get("materia"),
            assunto=meta.get("assunto"),
            banca=meta.get("banca"),
            orgao=meta.get("orgao"),
            cargo=meta.get("cargo"),
            ano=int(ano[:4]) if ano and ano[:4].isdigit() else None,
            enunciado=" ".join(e for e in enunciado if e) or None,
            alternativas=alternativas,
            gabarito=gabarito.get(numero),
            arquivo=arquivo,
        ))
    return questoes


def ler_pdf(caminho: Path) -> list[Questao]:
    import pdfplumber

    with pdfplumber.open(caminho) as pdf:
        texto = "\n".join(p.extract_text() or "" for p in pdf.pages)
    return parse_texto(texto, caminho.name)
