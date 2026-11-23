"""Planilha de Desempenho que chega por e-mail.

O TecConcursos não manda a planilha como anexo: o e-mail "Sua exportação de estatísticas está
pronta" traz um link temporário para um arquivo .xlsx. O e-mail diz que vale 7 dias, mas na prática
expira em poucas horas. Este módulo extrai esse link do código-fonte do e-mail e baixa o arquivo.

É o único ponto do projeto que acessa a rede, e só quando você roda
``tecconcursos-mcp baixar-email`` (por exemplo, a partir de uma regra do Mail). O servidor MCP
continua sem abrir conexões.
"""

from __future__ import annotations

import html
import quopri
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

_LINK = re.compile(r"""https://[^\s"'<>]+?\.amazonaws\.com/exports/[^\s"'<>]+""")


def extrair_link(fonte: bytes | str) -> str | None:
    """Link da planilha no código-fonte do e-mail (quoted-printable ou texto), ou None."""
    bruto = fonte.encode("utf-8", "ignore") if isinstance(fonte, str) else fonte
    texto = quopri.decodestring(bruto).decode("utf-8", "ignore")
    for achado in _LINK.findall(texto):
        url = html.unescape(achado)
        caminho = urllib.parse.urlparse(url).path
        if caminho.lower().endswith(".xlsx"):
            return url
    return None


def nome_do_arquivo(url: str) -> str:
    return Path(urllib.parse.urlparse(url).path).name or "tec_export.xlsx"


def baixar(url: str, pasta: Path, timeout: int = 60) -> Path:
    """Baixa a planilha para ``pasta`` com o nome do link. Erro se não vier um .xlsx."""
    host = urllib.parse.urlparse(url).hostname or ""
    if not host.endswith(".amazonaws.com"):
        raise ValueError(f"Link inesperado ({host}); só links de export do TecConcursos são aceitos.")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310 (host validado acima)
            dados = r.read()
    except urllib.error.HTTPError as e:
        corpo = e.read()[:500]
        if b"ExpiredToken" in corpo or b"AccessDenied" in corpo:
            raise ValueError("O link do e-mail expirou. Apesar de o e-mail dizer 7 dias, na prática ele vale "
                             "poucas horas: exporte de novo no TEC e rode logo que o e-mail chegar.") from e
        raise
    if not dados.startswith(b"PK"):
        raise ValueError("O link não devolveu uma planilha .xlsx (o link pode ter expirado).")
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / nome_do_arquivo(url)
    destino.write_bytes(dados)
    return destino
