# Instalação do servidor tecconcursos-mcp

Requer Python 3.10+ e [uv](https://docs.astral.sh/uv/getting-started/installation/).
O `uvx` baixa o código do GitHub (https://github.com/andrevinic/tecconcursos-mcp) na primeira execução;
depois disso o servidor roda localmente, via stdio, sem rede.

1. Crie a pasta de exports, por exemplo `~/TecConcursos/exports`.
2. Configure o seu agente com o modelo correspondente em `assets/mcp-config/`, trocando o caminho de
   `TEC_EXPORTS_DIR` pelo seu (caminho absoluto).
3. Reinicie o agente e peça: "mostra meu resumo geral do TecConcursos".

## Claude Code

```bash
claude mcp add tecconcursos \
  -e TEC_EXPORTS_DIR="$HOME/TecConcursos/exports" \
  -- uvx --from git+https://github.com/andrevinic/tecconcursos-mcp tecconcursos-mcp
```

## Claude Desktop
Settings → Developer → Edit Config, cole `assets/mcp-config/claude-desktop.json` dentro de `mcpServers`.

## Cursor
`~/.cursor/mcp.json` (global) ou `.cursor/mcp.json` (projeto): `assets/mcp-config/cursor.json`.

## VS Code / GitHub Copilot
`.vscode/mcp.json`: `assets/mcp-config/vscode.json`.

## Outros clientes MCP
Comando stdio: `uvx --from git+https://github.com/andrevinic/tecconcursos-mcp tecconcursos-mcp`,
com a variável de ambiente `TEC_EXPORTS_DIR`.

## CLI útil
- `tecconcursos-mcp importar`: copia planilhas novas de `~/Downloads` para a pasta de exports.
- `tecconcursos-mcp painel --abrir`: gera e abre o painel HTML offline.
(Para ter o comando no terminal: `uv tool install git+https://github.com/andrevinic/tecconcursos-mcp`.)
