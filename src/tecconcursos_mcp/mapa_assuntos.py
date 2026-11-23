"""Correspondência entre assuntos da mentoria (Tutory) e assuntos do TecConcursos.

Serve aos dois sentidos:

* **TEC → Tutory** (`assunto_tutory`): para lançar as questões de uma planilha de Desempenho por
  assunto, cada assunto-folha do TEC é levado ao assunto da mentoria que o contém.
* **Tutory → TEC** (`termos_tec`): para montar o caderno da semana no TEC a partir das metas da
  mentoria, cada assunto da meta vira os nomes de assunto a marcar no filtro do TEC.

Os termos são trechos de nomes do TEC, comparados sem acento e sem maiúsculas. Quando vários casam,
vence o termo mais longo (o mais específico). O que não casa vai para "Assunto Livre".

Os nomes dos assuntos da mentoria variam de plano para plano: acrescente ou corrija pares em
``mentoria.json`` → ``"assuntos": {"<assunto da mentoria>": ["trecho do TEC", ...]}``.
"""

from __future__ import annotations

from .models import normalizar

ASSUNTO_LIVRE = "Assunto Livre"

# disciplina (nome-base, sem acento) → {assunto da mentoria: [trechos de assuntos do TEC]}
PADRAO: dict[str, dict[str, list[str]]] = {
    "direito penal": {
        "Noções de Direito Penal: Princípios básicos": ["principios de direito penal", "principio da legalidade"],
        "A lei penal no tempo e no espaço": ["lei penal no tempo", "leis penais no tempo", "lei penal no espaco"],
        "Aplicação da lei penal": ["aplicacao da lei penal", "conflito aparente de normas"],
        "Tempo e lugar do crime": ["tempo do crime", "lugar do crime"],
        "Territorialidade e extraterritorialidade da lei penal": ["territorialidade", "extraterritorialidade"],
        "O fato típico e seus elementos": ["fato tipico", "conceito de crime", "conduta", "nexo causal", "resultado"],
        "Dolo e culpa": ["dolo, culpa", "dolo e culpa", "preterdolo"],
        "Erro": ["erro de tipo", "erro de proibicao", "erro sobre"],
        "Crime consumado e tentado": ["iter criminis", "fases do delito", "tentativa", "consumacao"],
        "Desistência voluntária e arrependimento eficaz": ["desistencia voluntaria", "arrependimento eficaz",
                                                            "arrependimento posterior"],
        "Crimes impossíveis": ["crime impossivel"],
        "Ilicitude e causas de exclusão": ["ilicitude", "legitima defesa", "estado de necessidade",
                                           "estrito cumprimento"],
        "Excesso punível": ["excesso punivel"],
        "Culpabilidade": ["culpabilidade", "imputabilidade"],
        "Concurso de pessoas": ["concurso de pessoas"],
        "Concurso de crimes": ["concurso de crimes"],
        "Crimes; Classificação": ["classificacoes dos crimes", "classificacao dos crimes"],
        "Pena: espécies e aplicação": ["das penas", "aplicacao da pena", "especies de pena"],
        "Extinção da punibilidade": ["extincao da punibilidade"],
        "Crimes contra o patrimônio": ["crimes contra o patrimonio", "do furto", "do roubo", "estelionato"],
        "Crimes contra a administração pública": ["crimes contra a administracao publica"],
        "Crimes contra a dignidade sexual": ["dignidade sexual"],
        "Crimes contra a Fé Pública": ["fe publica"],
        "Crimes contra a incolumidade pública": ["incolumidade publica"],
    },
    "direito processual penal": {
        "Inquérito policial": ["inquerito policial"],
        "Requisitos e ônus da prova": ["teoria geral da prova", "questoes mescladas sobre a prova", "onus da prova"],
        "Prova: Preservação de local de crime": ["corpo de delito", "cadeia de custodia", "pericias"],
        "Documentos de prova": ["dos documentos"],
        "Busca e apreensão": ["busca e apreensao"],
        "Reconhecimento de pessoas e coisas": ["reconhecimento de pessoas"],
        "Indícios": ["indicios"],
        "Nulidade da prova": ["provas ilicitas", "prova ilicita"],
        "Prisão em flagrante": ["prisao em flagrante"],
        "Prisão preventiva": ["prisao preventiva"],
        "Cautelares diversas": ["cautelares diversas"],
        "Liberdade Provisória": ["liberdade provisoria"],
        "Restrição de liberdade": ["disposicoes gerais e prisao especial", "prisao domiciliar", "prisao temporaria",
                                   "questoes mescladas sobre prisao"],
    },
    "direito constitucional": {
        "Conceito; Princípios Fundamentais": ["teoria do direito constitucional", "principios fundamentais"],
        "Direitos e garantias fundamentais": ["direitos e garantias fundamentais"],
        "Direitos Individuais": ["direitos e deveres individuais"],
        "Direitos Coletivos": ["direitos coletivos"],
        "Direitos Sociais": ["direitos sociais"],
        "Organização do Estado": ["organizacao do estado"],
        "Funções essenciais à Justiça": ["funcoes essenciais a justica"],
    },
    "lingua portuguesa": {
        "Regência verbal e nominal": ["regencia", "crase"],
        "Concordância verbal e nominal": ["concordancia"],
        "Pontuação e efeitos de sentido": ["pontuacao"],
        "Critérios de textualidade: coerência e coesão": ["coerencia", "coesao"],
        "Sintaxe: oração, período, termos das orações": ["sintaxe", "funcoes sintaticas", "termos essenciais"],
        "Articulação das orações: coordenação e subordinação": ["oracoes subordinadas", "oracoes coordenadas",
                                                                 "periodo composto"],
        "Conhecimentos gramaticais conforme padrão formal da língua": ["ortografia", "acentuacao"],
        "Recursos de construção textual: fonológicos, morfológicos, sintáticos e semânticos": ["morfologia",
                                                                                              "classes de palavras"],
        "Semântica: construção de sentido": ["semantica", "significacao"],
        "Sinonímia": ["sinonimos"],
        "Denotação e conotação": ["denotacao", "conotacao"],
        "Interpretação e compreensão de textos": ["interpretacao", "compreensao de texto"],
        "Figuras de linguagem": ["figuras de linguagem"],
    },
}


def _disciplina(nome: str) -> str:
    """'Direito Penal (VTM)' / 'Língua Portuguesa (Português)' → chave de PADRAO."""
    n = normalizar(nome)
    for chave in PADRAO:
        if n.startswith(chave):
            return chave
    if "constitucional" in n:
        return "direito constitucional"
    return n


def tabela(disciplina: str, extra: dict[str, list[str]] | None = None) -> dict[str, list[str]]:
    t = dict(PADRAO.get(_disciplina(disciplina), {}))
    for k, v in (extra or {}).items():
        t[k] = list(v)
    return t


def assunto_tutory(disciplina: str, caminho_tec: list[str], extra: dict[str, list[str]] | None = None) -> str:
    """Assunto da mentoria para um assunto-folha do TEC (caminho do mais geral ao mais específico).

    Procura primeiro na folha, depois nos níveis acima; dentro de um nível, vence o termo mais longo.
    """
    t = tabela(disciplina, extra)
    for nivel in reversed(caminho_tec):
        nome = normalizar(nivel)
        melhor = max(((len(termo), assunto) for assunto, termos in t.items() for termo in termos
                      if normalizar(termo) in nome), default=None)
        if melhor:
            return melhor[1]
    return ASSUNTO_LIVRE


def termos_tec(disciplina: str, assunto: str, extra: dict[str, list[str]] | None = None) -> list[str]:
    """Trechos de assunto do TEC para filtrar questões de uma meta da mentoria."""
    t = tabela(disciplina, extra)
    alvo = normalizar(assunto)
    for k, v in t.items():
        if normalizar(k) == alvo or normalizar(k).startswith(alvo) or alvo.startswith(normalizar(k)):
            return v
    return []
