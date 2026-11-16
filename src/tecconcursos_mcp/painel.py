"""Painel HTML estático (um arquivo, sem dependências, abre offline)."""

from __future__ import annotations

import json
from datetime import date
from html import escape
from typing import Any

from . import analysis
from .models import Snapshot

# Paleta categórica (ordem fixa) — claro / escuro.
CORES_CLARO = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
CORES_ESCURO = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#0ca30c", "#9085e9", "#e66767"]
MAX_SERIES = len(CORES_CLARO)


def _pct(v: float | None) -> str:
    return "—" if v is None else f"{v * 100:.0f}%".replace(".", ",")


def _data_br(iso: str) -> str:
    a, m, d = iso.split("-")
    return f"{d}/{m}/{a}"


def _grafico_linhas(prog: dict[str, Any], materias: list[str]) -> str:
    """Taxa de acerto por matéria, um ponto por planilha de Desempenho."""
    series = []
    for i, m in enumerate(materias):
        pts = [p for p in prog["materias"][m]["pontos"] if p.get("taxa_acerto") is not None]
        if pts:
            series.append((i, m, pts))
    datas = sorted({p["data"] for _, _, pts in series for p in pts})
    if not datas:
        return '<p class="vazio">Sem planilhas de Desempenho ainda: só elas têm acertos.</p>'

    L, R, T, B, W, H = 44, 16, 12, 28, 720, 260
    d0, d1 = date.fromisoformat(datas[0]), date.fromisoformat(datas[-1])
    span = max((d1 - d0).days, 1)

    def x(iso: str) -> float:
        if len(datas) == 1:
            return L + (W - L - R) / 2
        return L + (date.fromisoformat(iso) - d0).days / span * (W - L - R)

    def y(t: float) -> float:
        return T + (1 - t) * (H - T - B)

    partes = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="g1t" class="grafico">',
              '<title id="g1t">Taxa de acerto por matéria em cada planilha exportada</title>']
    for t in (0, 0.25, 0.5, 0.75, 1):
        partes.append(f'<line class="grade" x1="{L}" x2="{W - R}" y1="{y(t):.1f}" y2="{y(t):.1f}"/>'
                      f'<text class="eixo" x="{L - 6}" y="{y(t) + 4:.1f}" text-anchor="end">{int(t * 100)}%</text>')
    rotulos = datas if len(datas) <= 8 else datas[:: max(1, len(datas) // 6)] + [datas[-1]]
    for iso in dict.fromkeys(rotulos):
        partes.append(f'<text class="eixo" x="{x(iso):.1f}" y="{H - 8}" text-anchor="middle">{_data_br(iso)[:5]}</text>')
    for i, m, pts in series:
        cor = f"var(--s{i + 1})"
        if len(pts) > 1:
            d = " ".join(f"{'M' if k == 0 else 'L'}{x(p['data']):.1f},{y(p['taxa_acerto']):.1f}" for k, p in enumerate(pts))
            partes.append(f'<path d="{d}" fill="none" stroke="{cor}" stroke-width="2" stroke-linejoin="round"/>')
        for p in pts:
            dica = f"{m} · {_data_br(p['data'])}: {_pct(p['taxa_acerto'])} ({p['acertos']}/{p['resolvidas']})"
            partes.append(
                f'<g class="ponto" tabindex="0" data-dica="{escape(dica)}">'
                f'<circle cx="{x(p["data"]):.1f}" cy="{y(p["taxa_acerto"]):.1f}" r="12" fill="transparent"/>'
                f'<circle cx="{x(p["data"]):.1f}" cy="{y(p["taxa_acerto"]):.1f}" r="4.5" fill="{cor}" '
                f'stroke="var(--surface)" stroke-width="2"/></g>')
    partes.append("</svg>")
    legenda = "".join(
        f'<li><span class="chip" style="background:var(--s{i + 1})"></span>{escape(m)}'
        f' <strong>{_pct(pts[-1]["taxa_acerto"])}</strong></li>' for i, m, pts in series)
    return "".join(partes) + f'<ul class="legenda">{legenda}</ul>'


def _grafico_volume(geral: list[dict[str, Any]]) -> str:
    """Questões resolvidas por planilha: acertos + erros empilhados."""
    if not geral:
        return ""
    L, R, T, B, W, H = 44, 16, 12, 28, 720, 200
    maximo = max(p["resolvidas"] for p in geral) or 1
    n = len(geral)
    passo = (W - L - R) / n
    larg = min(48, passo * 0.6)

    def y(v: float) -> float:
        return T + (1 - v / maximo) * (H - T - B)

    partes = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="g2t" class="grafico">',
              '<title id="g2t">Questões resolvidas em cada planilha, com acertos e erros</title>']
    for frac in (0, 0.5, 1):
        v = round(maximo * frac)
        partes.append(f'<line class="grade" x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>'
                      f'<text class="eixo" x="{L - 6}" y="{y(v) + 4:.1f}" text-anchor="end">{v}</text>')
    for k, p in enumerate(geral):
        cx = L + passo * (k + 0.5)
        x0 = cx - larg / 2
        rotulo = _data_br(p["data"])[:5]
        partes.append(f'<text class="eixo" x="{cx:.1f}" y="{H - 8}" text-anchor="middle">{rotulo}</text>')
        if "acertos" in p:
            ac, er = p["acertos"], p["erros"]
            dica = f"{_data_br(p['data'])}: {p['resolvidas']} resolvidas · {ac} acertos · {er} erros"
            y_ac, y_tot = y(ac), y(ac + er)
            partes.append(f'<g class="ponto" tabindex="0" data-dica="{escape(dica)}">'
                          f'<rect x="{x0:.1f}" y="{y_ac:.1f}" width="{larg:.1f}" height="{y(0) - y_ac:.1f}" fill="var(--s1)"/>'
                          f'<rect x="{x0:.1f}" y="{y_tot:.1f}" width="{larg:.1f}" height="{max(0, y_ac - y_tot - 2):.1f}" '
                          f'rx="3" fill="var(--s2)"/></g>')
        else:
            dica = f"{_data_br(p['data'])}: {p['resolvidas']} resolvidas (planilha de Atividades, sem acertos)"
            partes.append(f'<g class="ponto" tabindex="0" data-dica="{escape(dica)}">'
                          f'<rect x="{x0:.1f}" y="{y(p["resolvidas"]):.1f}" width="{larg:.1f}" '
                          f'height="{y(0) - y(p["resolvidas"]):.1f}" rx="3" fill="var(--neutro)"/></g>')
    partes.append("</svg>")
    leg = ('<ul class="legenda"><li><span class="chip" style="background:var(--s1)"></span>Acertos</li>'
           '<li><span class="chip" style="background:var(--s2)"></span>Erros</li>'
           '<li><span class="chip" style="background:var(--neutro)"></span>Só contagem (Atividades)</li></ul>')
    return "".join(partes) + leg


def _tabela_fracos(snap: Snapshot | None) -> str:
    if snap is None or not snap.tem_acertos:
        return '<p class="vazio">Exporte a planilha de <strong>Desempenho</strong> para ver acertos por assunto.</p>'
    linhas = analysis.desempenho_assuntos(snap, nivel=None, min_questoes=2, ordenar="fracos", limite=12)
    if not linhas:
        return '<p class="vazio">Poucas questões por assunto ainda (mínimo 2).</p>'
    corpo = "".join(
        f"<tr><td>{escape(l['materia'])}</td>"
        f"<td>{escape(l.get('caminho') or l.get('assunto', ''))}</td>"
        f"<td class='num'>{l['acertos']}/{l['resolvidas']}</td>"
        f"<td class='num'><span class='barra' aria-hidden='true'><span style='width:{l['taxa_acerto'] * 100:.0f}%'></span></span>"
        f" {_pct(l['taxa_acerto'])}</td></tr>"
        for l in linhas)
    return ("<table><thead><tr><th scope='col'>Matéria</th><th scope='col'>Assunto</th>"
            "<th scope='col' class='num'>Acertos</th><th scope='col' class='num'>Taxa</th></tr></thead>"
            f"<tbody>{corpo}</tbody></table>")


def _tabela_dados(prog: dict[str, Any]) -> str:
    linhas = []
    for m, info in prog["materias"].items():
        for p in info["pontos"]:
            linhas.append(f"<tr><td>{_data_br(p['data'])}</td><td>{escape(m)}</td><td>{p['tipo']}</td>"
                          f"<td class='num'>{p['resolvidas']}</td><td class='num'>{p.get('acertos', '—')}</td>"
                          f"<td class='num'>{_pct(p.get('taxa_acerto'))}</td><td>{escape(p['arquivo'])}</td></tr>")
    return ("<table><thead><tr><th scope='col'>Data</th><th scope='col'>Matéria</th><th scope='col'>Planilha</th>"
            "<th scope='col' class='num'>Resolvidas</th><th scope='col' class='num'>Acertos</th>"
            "<th scope='col' class='num'>Taxa</th><th scope='col'>Arquivo</th></tr></thead>"
            f"<tbody>{''.join(linhas)}</tbody></table>")


def gerar_painel(snapshots: list[Snapshot]) -> str:
    prog = analysis.progresso(snapshots)
    ultimo = max((s for s in snapshots if s.tem_acertos), key=lambda s: (s.data, s.arquivo), default=None)
    ref = ultimo or max(snapshots, key=lambda s: (s.data, s.arquivo))
    ponto_ref = next(p for p in reversed(prog["geral"]) if p["arquivo"] == ref.arquivo)

    # matérias por volume na última planilha; cor fixa por matéria (ordem estável)
    materias = sorted(prog["materias"], key=lambda m: -sum(p["resolvidas"] for p in prog["materias"][m]["pontos"]))
    materias = materias[:MAX_SERIES]

    var = prog["variacao_geral"]
    var_txt = "—" if not var else f"{var['diferenca_pontos']:+.1f} p.p.".replace(".", ",")
    var_sub = ("exporte de novo em outra data para comparar" if not var
               else f"de {_data_br(var['de'])} a {_data_br(var['ate'])}")

    kpis = [
        ("Questões resolvidas", str(ponto_ref["resolvidas"]), f"planilha de {_data_br(ref.data)}"),
        ("Taxa de acerto", _pct(ponto_ref.get("taxa_acerto")), "na mesma planilha"),
        ("Evolução", var_txt, var_sub),
        ("Planilhas importadas", str(len(snapshots)), f"{len(prog['materias'])} matéria(s)"),
    ]
    kpi_html = "".join(f"<div class='kpi'><p class='rotulo'>{escape(a)}</p><p class='valor'>{escape(b)}</p>"
                       f"<p class='sub'>{escape(c)}</p></div>" for a, b, c in kpis)

    cores = "".join(f"--s{i + 1}:{c};" for i, c in enumerate(CORES_CLARO))
    cores_esc = "".join(f"--s{i + 1}:{c};" for i, c in enumerate(CORES_ESCURO))
    tema_escuro = f"--surface:#1a1a19;--bg:#121211;--ink:#f0efec;--ink2:#c3c2b7;--muted:#8d8c84;--grade:#383835;--neutro:#6b6a64;{cores_esc}color-scheme:dark;"

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Meu progresso TecConcursos</title>
<style>
:root {{
  --surface:#fcfcfb; --bg:#f4f3f0; --ink:#0b0b0b; --ink2:#52514e; --muted:#77766f; --grade:#e4e2dc; --neutro:#a9a79f;
  {cores}
  --espaco-sm:.5rem; --espaco-md:1rem; --espaco-lg:1.5rem; --raio:10px;
  --fonte: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  color-scheme: light;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ {tema_escuro} }} }}
:root[data-theme="dark"] {{ {tema_escuro} }}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 var(--fonte); }}
main {{ max-width: 960px; margin-inline:auto; padding: var(--espaco-lg) var(--espaco-md) 3rem; }}
header p {{ color:var(--ink2); margin-block:.25rem 0; }}
h1 {{ font-size:1.6rem; margin:0; }}
h2 {{ font-size:1.05rem; margin:0 0 var(--espaco-sm); }}
section {{ background:var(--surface); border-radius:var(--raio); padding:var(--espaco-md); margin-block-start:var(--espaco-md); }}
.kpis {{ display:grid; grid-template-columns:repeat(2,1fr); gap:var(--espaco-sm); margin-block-start:var(--espaco-md); }}
@media (min-width: 720px) {{ .kpis {{ grid-template-columns:repeat(4,1fr); }} }}
.kpi {{ background:var(--surface); border-radius:var(--raio); padding:var(--espaco-md); }}
.kpi p {{ margin:0; }}
.rotulo {{ color:var(--ink2); font-size:.85rem; }}
.valor {{ font-size:1.8rem; font-weight:650; font-variant-numeric:tabular-nums; }}
.sub {{ color:var(--muted); font-size:.8rem; }}
.grafico {{ width:100%; height:auto; display:block; overflow:visible; }}
.grade {{ stroke:var(--grade); stroke-width:1; }}
.eixo {{ fill:var(--muted); font-size:11px; font-family:var(--fonte); }}
.ponto {{ cursor:default; outline:none; }}
.ponto:focus-visible circle:last-child, .ponto:focus-visible rect {{ stroke:var(--ink); stroke-width:2; }}
.legenda {{ list-style:none; display:flex; flex-wrap:wrap; gap:.4rem 1.2rem; padding:0; margin:var(--espaco-sm) 0 0; color:var(--ink2); font-size:.85rem; }}
.chip {{ display:inline-block; width:10px; height:10px; border-radius:3px; margin-inline-end:.4rem; }}
.legenda strong {{ color:var(--ink); }}
.tabela {{ overflow-x:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:.88rem; }}
th, td {{ text-align:start; padding:.45rem .5rem; border-block-end:1px solid var(--grade); vertical-align:top; }}
th {{ color:var(--ink2); font-weight:600; }}
.num {{ text-align:end; font-variant-numeric:tabular-nums; white-space:nowrap; }}
.barra {{ display:inline-block; width:56px; height:6px; background:var(--grade); border-radius:3px; vertical-align:middle; margin-inline-end:.35rem; }}
.barra span {{ display:block; height:100%; background:var(--s1); border-radius:3px; }}
.vazio {{ color:var(--muted); margin:0; }}
details summary {{ cursor:pointer; color:var(--ink2); }}
.nota {{ color:var(--muted); font-size:.8rem; }}
#dica {{ position:fixed; pointer-events:none; background:var(--ink); color:var(--surface); padding:.35rem .55rem; border-radius:6px; font-size:.8rem; opacity:0; transition:opacity .1s; max-width:280px; }}
</style>
</head>
<body>
<main>
<header>
  <h1>Meu progresso no TecConcursos</h1>
  <p>Gerado a partir de {len(snapshots)} planilha(s) exportada(s), a mais recente de {_data_br(max(s.data for s in snapshots))}.</p>
</header>
<div class="kpis">{kpi_html}</div>
<section aria-labelledby="h-taxa"><h2 id="h-taxa">Taxa de acerto por matéria</h2>{_grafico_linhas(prog, materias)}</section>
<section aria-labelledby="h-vol"><h2 id="h-vol">Questões resolvidas por planilha</h2>{_grafico_volume(prog["geral"])}</section>
<section aria-labelledby="h-fracos"><h2 id="h-fracos">Assuntos para revisar</h2>
<p class="nota">Planilha de Desempenho de {_data_br(ultimo.data) if ultimo else "—"}; assuntos com 2+ questões, pior taxa primeiro.</p>
<div class="tabela">{_tabela_fracos(ultimo)}</div></section>
<section aria-labelledby="h-dados"><h2 id="h-dados">Dados</h2>
<details><summary>Ver tabela completa</summary><div class="tabela">{_tabela_dados(prog)}</div></details>
<p class="nota">Cada planilha cobre o período escolhido no site na hora de exportar. Para comparar pontos, exporte sempre com o mesmo tipo de período.</p>
</section>
</main>
<div id="dica" role="status" aria-live="polite"></div>
<script>
(() => {{
  const dica = document.getElementById("dica");
  const mostrar = (el, x, y) => {{
    dica.textContent = el.dataset.dica;
    const w = dica.offsetWidth;
    dica.style.left = Math.min(x + 12, innerWidth - w - 8) + "px";
    dica.style.top = (y - 36) + "px";
    dica.style.opacity = 1;
  }};
  for (const el of document.querySelectorAll(".ponto")) {{
    el.addEventListener("pointermove", e => mostrar(el, e.clientX, e.clientY));
    el.addEventListener("pointerleave", () => dica.style.opacity = 0);
    el.addEventListener("focus", () => {{ const r = el.getBoundingClientRect(); mostrar(el, r.right, r.top); }});
    el.addEventListener("blur", () => dica.style.opacity = 0);
  }}
}})();
</script>
</body>
</html>
"""
