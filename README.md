# tecconcursos-mcp

> ⚠️ **Projeto pessoal, independente e não oficial.** Não tem vínculo com TecConcursos,
> QConcursos, Tutory ou qualquer mentoria, nem é endossado por eles. Os nomes são marcas
> dos respectivos donos e aparecem aqui só para dizer com quais serviços a ferramenta funciona.
>
> O servidor **não abre conexões de rede**, não pede login, não guarda senhas ou cookies e
> **não baixa nem redistribui conteúdo das plataformas** (questões, comentários, aulas). Ele trabalha
> com **os seus próprios dados de desempenho**: arquivos que você exportou e números que você
> (ou seu assistente, no seu navegador e na sua sessão) leu das suas páginas de estatísticas.
> Veja [Uso responsável](#uso-responsável).

Servidor [MCP](https://modelcontextprotocol.io) que transforma seus dados de desempenho em
ferramentas para o Claude (ou qualquer cliente MCP). Com ele, você pode perguntar coisas como:

- *"Qual minha taxa de acerto por matéria?"*
- *"Quais assuntos de Direito Penal eu mais erro?"*
- *"Monta uma revisão com as questões de Física que errei na banca Cebraspe."*
- *"Acha as questões sobre cadeia de custódia nos meus cadernos."*

## Como tirar os dados do TecConcursos

O site tem export oficial em **Estatísticas**:

1. **Estatísticas → Desempenho**: escolha o período, marque **Selecionar Todos** e clique em
   **Exportar para planilha**. Essa planilha traz acertos e erros por matéria e assunto. Ela **chega por
   e-mail** em alguns minutos: salve o anexo `.xlsx` em `~/Downloads`.
2. (Opcional) **Estatísticas → Atividades** → *Exportar para planilha*. Baixa na hora, mas só traz quantas questões você resolveu.
3. Rode `tecconcursos-mcp importar`. O comando procura essas planilhas em `~/Downloads` pelo
   cabeçalho, copia para a pasta de exports como `desempenho_AAAA-MM-DD.xlsx` e pula as repetidas.

Cada planilha vira um **ponto na sua evolução**. Ela não diz o período que cobre: a data é a do
download. Para os pontos serem comparáveis, exporte sempre com o **mesmo tipo de período** (ex.: toda
domingo, "últimos 7 dias"). Se quiser registrar o período, renomeie para
`desempenho_2026-11-01_a_2026-11-07.xlsx`.

## Painel de progresso

```bash
tecconcursos-mcp importar        # traz os exports novos de ~/Downloads
tecconcursos-mcp painel --abrir  # gera <exports>/painel.html e abre no navegador
```

O painel é um HTML único que funciona offline: taxa de acerto por matéria ao longo do tempo,
questões por planilha, assuntos para revisar e a tabela completa. Tem tema claro e escuro.

## QConcursos (sem export)

O QConcursos não exporta, mas a página **Minhas Estatísticas** aceita qualquer período pela URL
(`/usuario/estatisticas/disciplinas?gt=AAAA-MM-DD&lt=AAAA-MM-DD`). O prompt **`coletar_qconcursos`**
orienta o Claude, no seu navegador já logado, a:

- ler a tabela de **Disciplina** e de **Assunto** de cada dia ainda não salvo;
- salvar cada dia com `salvar_estatisticas_qconcursos` em `qconcursos_AAAA-MM-DD.json`.

Os dias nunca se sobrepõem, então somar dá o total exato. O roteiro proíbe clicar em **"zerar"**,
que apaga as estatísticas no site.

- `progresso(fonte="qconcursos")` mostra um ponto por dia.
- `desempenho_assuntos(fonte="qconcursos")` soma todos os dias.
- `resumo_geral` e o painel mostram o QConcursos em bloco separado do TecConcursos.

Na página de Assuntos, uma questão pode contar em **vários assuntos** (o total por assunto passa do total
de questões) e não aparece a disciplina de cada assunto. Use os assuntos para achar pontos fracos, não para
somar volume.

## Lançar nas Metas Diárias da mentoria (Tutory)

Se sua mentoria usa a plataforma Tutory (página *Metas Diárias*), o Claude pode lançar ali as
questões que você fez no TecConcursos. O servidor **não acessa a mentoria**: ele só calcula o que
lançar, e quem preenche é o Claude no seu navegador (ex.: Claude in Chrome), **depois da sua confirmação**.

1. No TecConcursos, exporte o **Desempenho** do período ainda não lançado (ex.: hoje) e rode `tecconcursos-mcp importar`.
2. No Claude, use o prompt **`lancar_metas_mentoria`**. O roteiro é:
   - ler as metas de hoje;
   - `preparar_lancamentos_mentoria`, que casa cada meta com uma matéria do TEC ("Simulado de Língua Portuguesa (VTM)" → "Língua Portuguesa (Português)");
   - mostrar a tabela e pedir sua confirmação;
   - marcar "Meta concluída" e preencher *Questões feitas* / *Questões corretas*;
   - `registrar_lancamentos_mentoria`.
3. O que foi lançado fica em `mentoria_lancados.json`. A mesma planilha não é lançada duas vezes.

Opcional, `mentoria.json` na pasta de exports:

```json
{
  "url": "https://SUA-MENTORIA.tutory.com.br/painel/metas",
  "materias": { "Simulado de Direito Penal (VTM)": "Direito Penal" }
}
```

`materias` força pares meta → matéria do TEC quando o nome não bate sozinho.

## Ferramentas

**Planilhas oficiais de Estatísticas** (resumos por matéria e assunto):

| Ferramenta | O que faz |
|---|---|
| `desempenho_assuntos` | Acertos por matéria (`nivel=0`), assunto (`1`) ou subassunto (`2+`) na planilha mais recente; ordena por `fracos`, `fortes` ou `volume` |
| `progresso` | Evolução da taxa de acerto e do volume, um ponto por planilha, no total e por matéria |
| `preparar_lancamentos_mentoria` | Para cada meta do dia, a matéria do TEC e as questões/acertos a lançar |
| `salvar_estatisticas_qconcursos` | Grava as estatísticas de um dia do QConcursos (lidas da página pelo Claude) |
| `registrar_lancamentos_mentoria` | Anota localmente o que já foi lançado (única ferramenta que escreve, só na pasta de exports) |

**Exports por questão** (CSV/JSON/PDF de caderno):

| Ferramenta | O que faz |
|---|---|
| `resumo_geral` | Visão geral: última planilha de Estatísticas e/ou questões carregadas, taxa de acerto e período |
| `desempenho` | Taxa de acerto agrupada por `materia`, `assunto`, `banca`, `orgao`, `cargo` ou `ano`, com filtros |
| `pontos_fracos` | Grupos com pior desempenho, ignorando amostras pequenas (usa limite inferior de Wilson para desempatar) |
| `questoes_erradas` | Questões erradas, mais recentes primeiro, com filtros por matéria, assunto, banca e ano |
| `buscar_questao` | Busca por palavras no código, matéria, assunto, enunciado e alternativas |
| `listar_exports` | Arquivos encontrados, quantas questões cada um rendeu e erros de leitura |

Todas são somente leitura, exceto `salvar_estatisticas_qconcursos` e `registrar_lancamentos_mentoria`, que gravam só na pasta de exports. Os filtros de texto ignoram acentos e maiúsculas, e aceitam trechos
(`materia="penal"` encontra "Direito Penal").

## Formatos aceitos

Coloque os exports numa pasta, que pode ter subpastas. O servidor lê:

| Formato | Situação |
|---|---|
| `.xlsx` oficial de Estatísticas | ✅ Desempenho e Atividades (detectado pelo cabeçalho `Hierarquia`/`Índice`) |
| `.csv` / `.tsv` | ✅ Separador `,` `;` ou tab; UTF-8 ou Latin-1 |
| `.xlsx` (outros) | ✅ Todas as abas; a primeira linha é o cabeçalho |
| `.json` | ✅ Lista de objetos ou `{"questoes": [...]}` |
| `.pdf` (caderno) | 🧪 Experimental: usa heurísticas sobre o texto |

As colunas são reconhecidas por vários nomes. Por exemplo, `Matéria`/`Disciplina`, `Sua resposta`/`Resposta marcada`,
`Resultado`/`Situação`/`Acertou`. Se o export trouxer gabarito e resposta, o acerto é
calculado sozinho. A lista completa está em [`parsers/tabular.py`](src/tecconcursos_mcp/parsers/tabular.py).

Se a mesma questão aparecer em vários arquivos, fica a versão mais completa (a que tem resultado).

## Instalação

Requer [uv](https://docs.astral.sh/uv/getting-started/installation/).

### Claude Desktop

Edite o `claude_desktop_config.json`. No Claude Desktop, vá em *Settings → Developer → Edit Config*:

```json
{
  "mcpServers": {
    "tecconcursos": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/andrevinic/tecconcursos-mcp", "tecconcursos-mcp"],
      "env": { "TEC_EXPORTS_DIR": "/Users/voce/TecConcursos/exports" }
    }
  }
}
```

Reinicie o Claude Desktop. As ferramentas aparecem no menu de conectores da conversa.

### Claude Code

```bash
claude mcp add tecconcursos \
  -e TEC_EXPORTS_DIR="$HOME/TecConcursos/exports" \
  -- uvx --from git+https://github.com/andrevinic/tecconcursos-mcp tecconcursos-mcp
```

### Outros clientes MCP

O comando é `uvx --from git+https://github.com/andrevinic/tecconcursos-mcp tecconcursos-mcp`
(stdio), com a variável `TEC_EXPORTS_DIR` apontando para a pasta. Se você não definir a variável, a pasta padrão é
`~/TecConcursos/exports`.

## Uso responsável

Esta ferramenta foi feita para você acompanhar **o seu próprio estudo**. Ao usá-la:

- **Respeite os Termos de Uso de cada plataforma.** Você é responsável por como usa a sua conta. Na dúvida, use só o export oficial e consulte os termos do serviço.
- **Só os seus dados, na sua sessão.**
  - Nada aqui contorna login, paywall, captcha ou limite de acesso.
  - Não use a ferramenta para acessar dados de terceiros nem para coletar o acervo de questões dos sites.
- **Só números, não conteúdo.**
  - A coleta do QConcursos guarda contagens de certas/erradas por disciplina e o nome dos assuntos, nunca o texto das questões.
  - Não publique questões, gabaritos ou comentários das plataformas: são conteúdo protegido por direito autoral.
- **Volume humano.** Os roteiros leem uma página por vez, com pausa entre elas, e só quando você pede. Não os transforme em robôs agendados contra os sites.
- **Nada destrutivo.**
  - Os roteiros proíbem clicar em "zerar" estatísticas.
  - Os lançamentos na mentoria só acontecem depois da sua confirmação explícita, com os números mostrados antes.
- **Sem garantia.** As plataformas podem mudar páginas e termos a qualquer momento; a ferramenta pode parar de funcionar ou deixar de ser permitida. O software é fornecido "como está" (licença MIT).

## Privacidade

Tudo roda na sua máquina. O servidor não abre conexões de rede. Seus exports e coletas ficam na pasta de
exports (fora do repositório; o `.gitignore` também bloqueia `exports/`). O que vai para o modelo é só o que as
ferramentas devolvem: estatísticas e, em `questoes_erradas`/`buscar_questao`, o texto de questões que estejam
em arquivos seus. **Nunca faça commit dos seus exports.**

## Contribuindo

O PDF e os nomes de coluna variam, e é aí que a ajuda mais conta. Se um export seu não for reconhecido:

1. Rode `listar_exports` e veja o erro.
2. Abra uma issue com o **cabeçalho** das colunas, ou um trecho **anonimizado** do PDF.
   **Não publique questões, comentários nem estatísticas reais das plataformas**: use dados inventados.

Para desenvolver:

```bash
git clone https://github.com/andrevinic/tecconcursos-mcp && cd tecconcursos-mcp
uv run --extra dev pytest
```

Os testes usam só dados inventados. Mantenha assim.

## Licença

MIT. Veja [LICENSE](LICENSE).
