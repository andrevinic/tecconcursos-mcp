"""Fixtures 100% sintéticas: nenhuma questão real do TecConcursos é usada nos testes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

CSV_SINTETICO = """Código;Matéria;Assunto;Banca;Órgão;Cargo;Ano;Gabarito;Sua resposta;Data
900001;Direito Penal;Crimes contra a pessoa;Banca Alfa;Órgão X;Cargo Y;2021;C;C;2026-10-01
900002;Direito Penal;Crimes contra a pessoa;Banca Alfa;Órgão X;Cargo Y;2021;E;C;2026-10-02
900003;Direito Penal;Teoria do crime;Banca Beta;Órgão X;Cargo Y;2022;A;B;2026-10-03
900004;Física;Cinemática;Banca Alfa;Órgão Z;Cargo W;2020;B;B;2026-10-04
900005;Física;Cinemática;Banca Alfa;Órgão Z;Cargo W;2020;D;A;2026-10-05
900006;Física;Dinâmica;Banca Beta;Órgão Z;Cargo W;2023;C;C;2026-10-06
"""

JSON_SINTETICO = {
    "questoes": [
        {"id": "900007", "disciplina": "Química", "assunto": "Estequiometria",
         "banca": "Banca Beta", "ano": 2024, "enunciado": "Enunciado inventado sobre mols.",
         "resultado": "errou"},
        # repetida do CSV, sem resultado: não pode sobrescrever a versão respondida
        {"id": "900001", "disciplina": "Direito Penal"},
    ]
}

PDF_TEXTO = """Caderno de teste
1) 900101 Banca: Banca Alfa - Órgão: Órgão X - Cargo: Cargo Y - Ano: 2019
Matéria: Informática - Assunto: Redes
Enunciado inventado sobre protocolos de rede.
a) Opção um
b) Opção dois
c) Opção três
2) 900102 Banca: Banca Beta - Ano: 2020
Matéria: Informática - Assunto: Segurança
Julgue o item inventado a seguir.
Gabarito
1) B 2) Certo
"""


@pytest.fixture
def pasta_exports(tmp_path: Path) -> Path:
    (tmp_path / "estatisticas.csv").write_text(CSV_SINTETICO, encoding="utf-8")
    (tmp_path / "extra.json").write_text(json.dumps(JSON_SINTETICO), encoding="utf-8")
    (tmp_path / "ignorar.txt").write_text("não é export", encoding="utf-8")
    return tmp_path
