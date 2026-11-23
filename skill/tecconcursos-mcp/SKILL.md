---
name: tecconcursos-mcp
description: Analisa o seu próprio desempenho nos estudos para concursos públicos (TecConcursos e QConcursos) a partir de arquivos que você exportou, usando o servidor MCP local tecconcursos-mcp. Use quando o estudante perguntar sobre taxa de acerto, pontos fracos, evolução, questões erradas ou revisão por matéria, assunto ou banca.
when_to_use: Perguntas como "qual minha taxa de acerto por matéria?", "quais assuntos de Penal eu mais erro?", "como evoluí em Português?", "monta uma revisão com as questões que errei da Cebraspe".
---

# tecconcursos-mcp

Projeto pessoal, independente e **não oficial**: não tem vínculo com TecConcursos, QConcursos ou Tutory.
O servidor roda na máquina do usuário, **não abre conexões de rede** e só lê arquivos que o próprio
usuário exportou para a pasta `TEC_EXPORTS_DIR` (padrão `~/TecConcursos/exports`).

## Antes de tudo: o servidor está instalado?

Se as ferramentas `tecconcursos` (ex.: `resumo_geral`) não aparecerem, o servidor MCP ainda não foi
configurado. Siga `references/setup.md` e use o modelo de configuração do agente em `assets/mcp-config/`.
Não invente números: sem as ferramentas, explique como instalar.

## Fluxo padrão

1. Comece sempre por `resumo_geral`: mostra o que há na pasta (planilhas de Estatísticas e/ou questões).
2. Se não houver dados, oriente o export (abaixo) e `tecconcursos-mcp importar`. Use `listar_exports`
   para ver erros de leitura.
3. Escolha a ferramenta pelo tipo de dado:

**Planilhas oficiais de Estatísticas** (resumo por matéria/assunto, uma por data):

| Pergunta | Ferramenta |
|---|---|
| Acerto por matéria / assunto / subassunto | `desempenho_assuntos(nivel=0/1/2, ordenar="fracos"/"fortes"/"volume")` |
| Evolução no tempo | `progresso(materia=...)` |
| QConcursos | as mesmas, com `fonte="qconcursos"` |

**Exports por questão** (CSV/JSON/XLSX/PDF de caderno):

| Pergunta | Ferramenta |
|---|---|
| Acerto agrupado | `desempenho(agrupar_por="materia"/"assunto"/"banca"/"orgao"/"cargo"/"ano")` |
| Onde focar | `pontos_fracos(min_questoes=5)` (ignora amostras pequenas) |
| Lista para revisão | `questoes_erradas(materia, assunto, banca, ano)` |
| Achar uma questão | `buscar_questao(texto)` |

Filtros de texto aceitam trechos sem acento (`materia="penal"` encontra "Direito Penal").

## Como o usuário exporta do TecConcursos

**Estatísticas → Desempenho** → escolha o período → **Selecionar Todos** → **Exportar para planilha**.
A planilha chega por e-mail; salve o `.xlsx` em `~/Downloads` e rode `tecconcursos-mcp importar`.
Para comparar a evolução, exporte sempre o mesmo tipo de período (ex.: "últimos 7 dias", todo domingo).
`tecconcursos-mcp painel --abrir` gera um painel HTML offline.

## Como responder

- Mostre taxa de acerto **com o número de questões** (60% em 5 questões não é 60% em 500).
- Ao apontar pontos fracos, priorize assuntos com volume suficiente e sugira próximos passos concretos.
- Na planilha de Assuntos do QConcursos uma questão conta em vários assuntos: não some volumes.

## Planilha por e-mail
O export de Desempenho chega por e-mail **com um link** (não anexo, vale 7 dias). Com o código-fonte do
e-mail, `tecconcursos-mcp baixar-email email.eml` baixa e importa, descartando exports repetidos. No Mac há
uma regra do Mail pronta em `extras/mail/` do repositório.

## Fluxos opcionais (prompts do servidor)

- `coletar_qconcursos`: lê, no navegador já logado do usuário, as estatísticas do dia e salva com
  `salvar_estatisticas_qconcursos`. **Nunca clique em "zerar"** estatísticas. Uma página por vez, só quando pedido.
- `caderno_da_semana`: lê o Resumo da Semana da mentoria, chama `planejar_caderno_semana` (assuntos do TEC
  e nº de questões por meta), **mostra o plano e pede confirmação**, e só então cria UM caderno no TEC
  ("Semana AAAA-MM-DD · Tutory"). Nunca apague nem altere cadernos existentes.
- `lancar_metas_mentoria`: use `preparar_lancamentos_por_assunto` para lançar **por assunto e na data certa**
  na página "Lançamentos de Questões"; a lixeira de lá apaga todas as linhas idênticas, então nunca deixe
  duplicatas. Se pedir login, peça ao usuário (nunca digite senha).
- `lancar_metas_mentoria` (metas do dia): `preparar_lancamentos_mentoria` → **mostre a tabela e peça confirmação
  explícita** → preencha → `registrar_lancamentos_mentoria`. Nunca preencha sem confirmação.

## Limites

- Só os dados do próprio usuário. Não colete acervo de questões nem dados de terceiros.
- Não publique nem redistribua questões, gabaritos ou comentários das plataformas (direito autoral).
- Respeite os Termos de Uso de cada plataforma.

Código-fonte (MIT): https://github.com/andrevinic/tecconcursos-mcp
