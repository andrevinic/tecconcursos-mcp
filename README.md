# tecconcursos-mcp

> ⚠️ **Projeto não oficial.** Não tem vínculo com o TecConcursos nem é endossado por ele.
> O servidor **não acessa o site**, não pede login e não faz scraping: ele só lê os
> arquivos que **você mesmo exportou** e que estão no seu computador.

Servidor [MCP](https://modelcontextprotocol.io) que transforma seus exports do
TecConcursos em ferramentas para o Claude (ou qualquer cliente MCP). Com ele, você pode perguntar coisas como:

- *"Qual minha taxa de acerto por matéria?"*
- *"Quais assuntos de Direito Penal eu mais erro?"*
- *"Monta uma revisão com as questões de Física que errei na banca Cebraspe."*
- *"Acha as questões sobre cadeia de custódia nos meus cadernos."*

## Ferramentas

| Ferramenta | O que faz |
|---|---|
| `resumo_geral` | Questões carregadas, respondidas, taxa de acerto e período |
| `desempenho` | Taxa de acerto agrupada por `materia`, `assunto`, `banca`, `orgao`, `cargo` ou `ano`, com filtros |
| `pontos_fracos` | Grupos com pior desempenho, ignorando amostras pequenas (usa limite inferior de Wilson para desempatar) |
| `questoes_erradas` | Questões erradas, mais recentes primeiro, com filtros por matéria, assunto, banca e ano |
| `buscar_questao` | Busca por palavras no código, matéria, assunto, enunciado e alternativas |
| `listar_exports` | Arquivos encontrados, quantas questões cada um rendeu e erros de leitura |

Todas são somente leitura. Os filtros de texto ignoram acentos e maiúsculas, e aceitam trechos
(`materia="penal"` encontra "Direito Penal").

## Formatos aceitos

Coloque os exports numa pasta, que pode ter subpastas. O servidor lê:

| Formato | Situação |
|---|---|
| `.csv` / `.tsv` | ✅ Separador `,` `;` ou tab; UTF-8 ou Latin-1 |
| `.xlsx` | ✅ Todas as abas; a primeira linha é o cabeçalho |
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

## Privacidade

Tudo roda na sua máquina. O servidor não abre conexões de rede. O que vai para o modelo é só
o que as ferramentas devolvem: estatísticas e, em `questoes_erradas`/`buscar_questao`, o texto das
questões encontradas.

## Contribuindo

O PDF e os nomes de coluna variam, e é aí que a ajuda mais conta. Se um export seu não for reconhecido:

1. Rode `listar_exports` e veja o erro.
2. Abra uma issue com o **cabeçalho** das colunas, ou um trecho **anonimizado** do PDF.
   **Não publique questões nem comentários do TecConcursos**: eles são conteúdo protegido.

Para desenvolver:

```bash
git clone https://github.com/andrevinic/tecconcursos-mcp && cd tecconcursos-mcp
uv run --extra dev pytest
```

Os testes usam só dados inventados. Mantenha assim.

## Licença

MIT. Veja [LICENSE](LICENSE).
