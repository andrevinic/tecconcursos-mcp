"""Copia a semana do Tutory para o calendário "Estudos" do iCloud (aparece no iPhone e no Fantastical).

Uso: python3 calendario_tutory.py semana.json

semana.json:
{
  "limpar_de": "2026-11-23", "limpar_ate": "2026-11-29",
  "eventos": [{"data": "2026-11-23", "inicio": "20:00", "min": 15,
               "titulo": "Proc. Penal · Simulado", "notas": "..."}]
}

Apaga só os eventos com nota começando em "Tutory:" no intervalo e cria os novos (alerta 10 min antes).
Os blocos fixos (nota "Bloco:") não são tocados. Usa ./ekcal (EventKit), porque calendários criados por
AppleScript ficam só no Mac e não sincronizam com o iCloud.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
EKCAL = AQUI / "ekcal"
CAL = "Estudos"
URL = os.environ.get("TUTORY_METAS_URL", "")


def main() -> None:
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    eventos = [{
        "titulo": e["titulo"],
        "inicio": f'{e["data"]} {e["inicio"]}',
        "min": int(e["min"]),
        "notas": "Tutory: " + e.get("notas", "").removeprefix("Tutory: "),
        **({"url": URL} if URL else {}),
        "alerta": 10,
    } for e in cfg["eventos"]]
    r1 = subprocess.run([EKCAL, "delete-range", CAL, cfg["limpar_de"], cfg["limpar_ate"], "Tutory:"],
                        capture_output=True, text=True)
    print(r1.stdout.strip() or r1.stderr.strip())
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(eventos, f, ensure_ascii=False)
    r2 = subprocess.run([EKCAL, "add", CAL, f.name], capture_output=True, text=True)
    print(r2.stdout.strip() or r2.stderr.strip())
    Path(f.name).unlink(missing_ok=True)
    sys.exit(r1.returncode or r2.returncode)


if __name__ == "__main__":
    main()
