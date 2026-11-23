# Calendário de estudos (macOS, opcional)

Copia as metas da semana da mentoria para um calendário **"Estudos" no iCloud**, que aparece no iPhone e em
apps como o Fantastical.

- `ekcal.swift`: ferramenta mínima sobre o EventKit (cria calendário no iCloud, adiciona e apaga eventos).
  Calendários criados por AppleScript ficam só no Mac ("No Meu Mac") e o iCloud desfaz exclusões de séries
  feitas por AppleScript; o EventKit não tem esses problemas.
- `calendario_tutory.py`: recebe a semana em JSON e substitui só os eventos marcados com `Tutory:`; blocos
  fixos (`Bloco:`) ficam intactos.

```bash
swiftc -O -o ekcal ekcal.swift          # na primeira vez o macOS pede acesso aos calendários
./ekcal ensure "Estudos"
python3 calendario_tutory.py semana.json
```

`semana.json`:

```json
{"limpar_de": "2026-11-23", "limpar_ate": "2026-11-29",
 "eventos": [{"data": "2026-11-24", "inicio": "20:00", "min": 30, "titulo": "Penal · Princípios (exercícios)", "notas": "..."}]}
```

A mentoria não exporta calendário: quem lê o "Resumo da Semana" é o assistente, no navegador da pessoa.
