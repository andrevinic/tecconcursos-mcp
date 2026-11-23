"""Linha de comando.

    tecconcursos-mcp                          # servidor MCP (stdio), como antes
    tecconcursos-mcp importar                 # copia planilhas oficiais de ~/Downloads para a pasta de exports
    tecconcursos-mcp baixar-email email.eml   # baixa a planilha do link do e-mail do TEC e importa
    tecconcursos-mcp painel --abrir           # gera um painel HTML com sua evolução
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import tempfile
import webbrowser
from datetime import date
from pathlib import Path

from .parsers.estatisticas import eh_planilha_estatisticas, ler_snapshot_xlsx, primeira_linha_xlsx


def _hash(p: Path) -> str:
    """Assinatura do CONTEÚDO das células: o TEC gera um arquivo novo (bytes e nome diferentes)
    a cada export, mesmo quando os números são os mesmos."""
    try:
        import openpyxl

        ws = openpyxl.load_workbook(p, read_only=True).active
        h = hashlib.sha256()
        for linha in ws.iter_rows(values_only=True):
            h.update(repr(linha).encode("utf-8"))
        return "celulas:" + h.hexdigest()
    except Exception:
        return "bytes:" + hashlib.sha256(p.read_bytes()).hexdigest()


def importar(origem: Path, destino: Path, mover: bool = False) -> list[tuple[Path, Path | None, str]]:
    """Procura planilhas oficiais (pelo cabeçalho) em ``origem`` e copia para ``destino``
    como ``desempenho_AAAA-MM-DD.xlsx``/``atividades_AAAA-MM-DD.xlsx``.

    A data é a da modificação do arquivo (= quando você exportou). Planilhas com as mesmas
    células de alguma já importada são puladas. Devolve (origem, destino ou None, motivo).
    """
    destino.mkdir(parents=True, exist_ok=True)
    existentes = {_hash(p) for p in destino.rglob("*.xlsx") if p.is_file()}
    resultado = []
    for arq in sorted(origem.glob("*.xlsx"), key=lambda p: p.stat().st_mtime):
        if arq.name.startswith(("~$", ".")):
            continue
        try:
            if not eh_planilha_estatisticas(primeira_linha_xlsx(arq)):
                continue
            snap = ler_snapshot_xlsx(arq)
        except Exception:
            continue
        if snap is None:
            continue
        h = _hash(arq)
        if h in existentes:
            resultado.append((arq, None, "já importada"))
            continue
        dia = date.fromtimestamp(arq.stat().st_mtime).isoformat()
        alvo = destino / f"{snap.tipo}_{dia}.xlsx"
        n = 2
        while alvo.exists():
            alvo = destino / f"{snap.tipo}_{dia}_{n}.xlsx"
            n += 1
        (shutil.move if mover else shutil.copy2)(str(arq), str(alvo))
        existentes.add(h)
        resultado.append((arq, alvo, "importada"))
    return resultado


def main(argv: list[str] | None = None) -> None:
    from .server import PASTA_PADRAO, pasta_exports

    ap = argparse.ArgumentParser(prog="tecconcursos-mcp", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("servidor", help="roda o servidor MCP via stdio (padrão)")

    imp = sub.add_parser("importar", help="copia planilhas oficiais baixadas para a pasta de exports")
    imp.add_argument("--de", type=Path, default=Path("~/Downloads"), help="pasta de origem (padrão: ~/Downloads)")
    imp.add_argument("--para", type=Path, default=None,
                     help=f"pasta de exports (padrão: $TEC_EXPORTS_DIR ou {PASTA_PADRAO})")
    imp.add_argument("--mover", action="store_true", help="move em vez de copiar")

    em = sub.add_parser("baixar-email", help="baixa a planilha do link do e-mail do TEC e importa")
    em.add_argument("fonte", help="arquivo com o código-fonte do e-mail (.eml), ou - para ler da entrada padrão")
    em.add_argument("--para", type=Path, default=None,
                    help=f"pasta de exports (padrão: $TEC_EXPORTS_DIR ou {PASTA_PADRAO})")

    pai = sub.add_parser("painel", help="gera um painel HTML com sua evolução")
    pai.add_argument("--saida", type=Path, default=None, help="arquivo HTML (padrão: <exports>/painel.html)")
    pai.add_argument("--abrir", action="store_true", help="abre no navegador")

    args = ap.parse_args(argv)

    if args.cmd in (None, "servidor"):
        from .server import mcp

        mcp.run("stdio")
        return

    if args.cmd == "importar":
        destino = (args.para or pasta_exports()).expanduser()
        res = importar(args.de.expanduser(), destino, args.mover)
        novas = [r for r in res if r[1]]
        for orig, alvo, motivo in res:
            print(f"{motivo:>13}: {orig.name}" + (f" -> {alvo}" if alvo else ""))
        if not res:
            print(f"Nenhuma planilha de Estatísticas do TecConcursos em {args.de}.")
        print(f"{len(novas)} nova(s) em {destino}")
        return

    if args.cmd == "baixar-email":
        from . import email_tec

        fonte = sys.stdin.buffer.read() if args.fonte == "-" else Path(args.fonte).expanduser().read_bytes()
        url = email_tec.extrair_link(fonte)
        if not url:
            print("sem link de planilha neste e-mail")
            return
        destino = (args.para or pasta_exports()).expanduser()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                arq = email_tec.baixar(url, Path(tmp))
            except Exception as e:  # link expirado, sem rede ou host inesperado
                print(f"falha ao baixar: {e}")
                sys.exit(1)
            res = importar(Path(tmp), destino)
        if not res:
            print(f"{arq.name}: não é uma planilha de Estatísticas do TecConcursos")
        for _, alvo, motivo in res:
            print(f"{motivo}: {alvo}" if alvo else f"{motivo} (mesmas células de uma planilha já importada)")
        return

    if args.cmd == "painel":
        from .painel import gerar_painel
        from .parsers import carregar_pasta

        pasta = pasta_exports()
        bib = carregar_pasta(pasta)
        if not bib.snapshots:
            print(f"Nenhuma planilha de Estatísticas em {pasta}. Rode `tecconcursos-mcp importar` antes.",
                  file=sys.stderr)
            sys.exit(1)
        saida = (args.saida or pasta / "painel.html").expanduser()
        saida.write_text(gerar_painel(bib.snapshots), encoding="utf-8")
        print(f"Painel gerado: {saida}")
        if args.abrir:
            webbrowser.open(saida.resolve().as_uri())


if __name__ == "__main__":
    main()
