# Changelog

All notable changes to this replication package are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — não lançada (aguardando sign-off do operador)

Primeira publicação do pacote de replicação e do artigo.

### Adicionado

- Artigo completo em PT-BR com abstract em inglês (`docs/paper/paper-final.docx` e `.pdf`),
  no padrão da casa (APA 7 na camada pública).
- Seção **"Disponibilidade de código e dados"** no artigo, nomeando este repositório e
  declarando que o conjunto ULB/Worldline **não é redistribuído** (obtido por script com
  verificação SHA-256).
- Auto-referência `Flores (2026)` na lista de referências: as quatro menções ao "pacote de
  replicação" no corpo passam a ter endereço.
- `.github/workflows/ci.yml` — testes, `compileall` e **verificação de integridade do run
  selado** (o manifest cobre scripts, configs e saídas).
- `CHANGELOG.md` (este arquivo).
- `version: 1.0.0` em `.zenodo.json`.

### Corrigido

- **Vazamento de caminho absoluto no DOCX.** O atributo `descr` da logo da capa carregava o
  caminho do workspace privado. Causa-raiz no gerador (`scripts/make_apa7_export.py`): imagem
  sem *alt text* faz o pandoc escrever o caminho no `descr`, e um segundo `descr`
  (`<pic:cNvPr>`) recebe o caminho mesmo com alt preenchido. Corrigido nas duas pontas — alt
  text em todas as imagens **e** caminho relativo para a logo. Verificado por varredura do
  `.docx` como zip: zero ocorrências de `/Users/` e `research-lab`.
- Badge de testes: `18/18` → **`24/24`** (número real da suíte).
- Bloco BibTeX do README: removido o texto *"Zenodo DOI to be minted"* (placeholder); a
  entrada passa a apontar a URL do repositório. O DOI entra na versão seguinte, após o mint.
- Nome do repositório propagado para `CITATION.cff`, `.zenodo.json`, `codemeta.json` e
  `pyproject.toml`.

### Dívida declarada (não corrigível sem re-rodar o experimento)

O manifest `runs/20260704T204343Z/checksums.sha256` sela o SHA-256 dos sete scripts. Editar
qualquer um deles fora de um re-run quebra a cadeia dados→resultados. Ficam para o próximo run:

- Cobertura de docstrings em **50% (41/82)** contra o padrão de 100% da casa.
- 13 achados de `ruff` em `scripts/` (nenhum de correção, todos de estilo/robustez).
- Mirror morto (`datahub.io`, HTTP 404) na lista de `scripts/get_data.py`; o mirror primário
  responde 200 e o script os tenta em ordem, então a replicação não é afetada. Documentado no
  README em vez de corrigido no arquivo selado.

### Pendente de publicação (human-gated)

Push, release e mint do DOI Zenodo exigem sign-off do operador. Após o mint, o DOI é inserido
apenas em metadado **não selado** (`CITATION.cff`, `.zenodo.json`, badge do README) na versão
`1.0.1`, sem re-selar o artigo — a dança de duas releases descrita em
`metodo/regras/cunhagem-doi-zenodo.md`.
