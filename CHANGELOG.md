# Changelog

All notable changes to this replication package are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] — 2026-08-01

Duas mudanças de fundo: a capa deixa de carregar um vínculo institucional que não pertence a este
artefato público, e o pacote passa a publicar o artigo **em duas edições** — português e inglês —
lado a lado. **Nenhum arquivo selado pelo manifest é tocado:** a cadeia de
`runs/20260704T204343Z/checksums.sha256` foi reconferida com **0 falhas** depois de tudo, e as
figuras em inglês são geradas por um script **não selado** que escreve num diretório **não selado**
(`output/figures-en/`), respeitando o invariante de replicação.

### Corrigido

- **Capa: removida a linha de vínculo acadêmico** e a afiliação passou a ser
  `Codex Hash Research Laboratory` (a forma canônica do perfil). Este é o motivo da versão: o DOCX
  e o PDF da 1.0.1 carregavam a titulação, que é confidencial e não pertence a um artefato público.
  A suíte de testes passou a **barrar as duas grafias** (PT e EN) em qualquer membro do DOCX, de
  modo que a regressão não pode voltar sem quebrar o CI.

### Adicionado

- **Edição em inglês do artigo** — `docs/paper/paper-final-en.pdf` e `.docx` (29 páginas, APA 7).
  Mesmos dados, mesmos números, mesma tese: o multiconjunto de números do corpo PT e do corpo EN é
  **idêntico** (665 números, verificado por código, com os separadores normalizados), e as 39
  URLs/DOIs também. Os títulos das duas auto-citações (Flores, 2025 e Flores, 2026) entram **em
  português, verbatim**, com glosa em inglês entre colchetes: o depósito Zenodo é imutável e traduzir
  o título ali seria citar uma obra que não existe.
- **Figuras em inglês sem re-executar o experimento** — `scripts/make_figures_en.py` importa o
  `make_figures.py` selado e traduz os rótulos no caminho para o matplotlib, lendo os mesmos insumos
  selados e escrevendo em `output/figures-en/`. Nenhum byte selado muda.
- **Pipeline de export por idioma** — `scripts/build_export.sh [pt-BR|en]`. As quebras de página
  passaram a ser lidas do contrato da casa por idioma, em vez de uma lista fixa em português, e a
  língua de revisão do DOCX passa a `en-US` na edição inglesa.
- **Cobertura de testes nas duas edições** — o contrato de export era verificado só no artefato PT;
  agora roda nos dois (6 -> 13 testes), incluindo um teste de que as duas edições são documentos
  genuinamente distintos. Somado ao novo `tests/test_metadata.py`, a suíte vai de **24 a 33**.
- **Aviso de reprodutibilidade que faltava** — `REPRODUCIBILITY.md` agora explica que **um re-run
  legítimo também derruba o `sha256sum -c`** (15 dos 37, todos arquivos de figura, por causa de
  `/CreationDate`, `<dc:date>` e IDs aleatórios do matplotlib) e ensina a conferir por conteúdo
  depois de re-rodar. Sem isso, quem replica lê 15 `FAILED` e conclui adulteração.
- **Trava contra release meio-feita** — `tests/test_metadata.py` assere que a versão é a mesma em
  `CITATION.cff`, `.zenodo.json`, `codemeta.json` e `pyproject.toml`, e que ela concorda com o
  CHANGELOG (enquanto o topo estiver `Unreleased`, o metadado tem de continuar na última versão
  publicada). Bumpar três dos quatro publicaria um depósito Zenodo — **imutável** — exibindo a
  versão errada.

- **README no padrão de publicação da casa** — callout `> [!IMPORTANT]` com os números-manchete,
  seção **"What is and isn't claimed"** (o que se afirma, o que **não** se afirma — 74 positivos no
  teste, ausência de evidência ≠ equivalência, nada sobre "fraude em geral" — e o que está
  congelado), seção **Integrity** com o comando de verificação, e bloco **Author** com ORCID,
  site e Lattes.
- **`ROADMAP.md`** — o que vem depois, com o custo medido na frente: o re-run que paga a dívida
  declarada de uma vez, o notebook de replicação zero-setup, a validação externa em benchmark com
  partição temporal, e o que **não** está planejado (entrada em leaderboard, virar biblioteca).
- **Alvo de lint declarado no `pyproject.toml`** — `ruff` (`E,F,W,I,UP,B,D`, pydocstyle numpy),
  `interrogate fail-under = 100` e `pytest testpaths`. O código **não selado** (`run_all.py`,
  `tests/`) foi trazido para o alvo e passa limpo; `scripts/` é selado e continua com a dívida
  declarada, reportada pelo job informacional. Afrouxar o alvo para o CI ficar verde seria mentir
  sobre o padrão — o alvo fica no arquivo, honesto.

### Dívida declarada (nova)

- **O slug do projeto com data (`2025-fraud-detection-mlp`) está dentro do registro selado** —
  `runs/20260704T204343Z/manifest.json` e `scripts/make_run.py`. Corrigir exigiria re-executar o
  experimento inteiro, e a re-execução foi medida: **742 de 743 campos** de `output/results.json`
  saem idênticos (o único que muda é `runtime_seconds`, tempo de parede) e os 7 PNG são
  bit-idênticos. Ou seja, o re-run compraria cosmética de nome ao preço de re-selar a cadeia toda.
  O nome com data fica registrado aqui como o que era verdade na execução de 2026-07-04; o campo
  passa a refletir o nome definitivo **a partir do próximo run**.

## [1.0.1] — 2026-07-30

Backfill do DOI cunhado. Esta é a **versão superseding** prevista pela dança de duas releases
(`metodo/regras/cunhagem-doi-zenodo.md`): é nela que o DOI entra **no próprio artigo**, o que a
regra permite exatamente por ser uma versão nova, e não uma re-selagem sob o mesmo DOI.
**Nenhum artefato selado pelo manifest é tocado** — `docs/paper/` não está entre os 37 arquivos de
`runs/20260704T204343Z/checksums.sha256`, e a cadeia foi reconferida com **0 falhas** depois do
re-export.

### Adicionado

- **Concept DOI `10.5281/zenodo.21708708`** (umbrella; resolve sempre para a versão mais
  recente) em `CITATION.cff` (`doi` e `preferred-citation.doi`), `codemeta.json`
  (`identifier`), badge e seção *Citation* do `README.md`, e no bloco BibTeX.
- Version DOI da release 1.0.0 (`10.5281/zenodo.21708709`) registrado no README como âncora
  de proveniência da release.
- **O DOI na auto-referência do artigo**, no formato do precedente publicado: `… Codex Hash
  Research Laboratory. Zenodo. https://doi.org/10.5281/zenodo.21708708. Repositório de código:
  …`. O artigo foi re-exportado (DOCX + PDF), mantendo as **31 páginas**, com varredura de leak
  limpa nos 50 streams do PDF e no DOCX como zip, e os **24 testes** verdes — inclusive
  `test_export.py`, que valida o DOCX publicado.

### Corrigido

- `version` subiu para `1.0.1` em `CITATION.cff`, `.zenodo.json`, `codemeta.json` e
  `pyproject.toml` — é a 1.0.1 que o Zenodo arquiva nesta release, e o metadado precisa dizer
  isso.

### Nota de manutenção (armadilha encontrada nesta versão)

A lista de referências existe em **dois lugares**: o `docs/paper/paper-final.md` canônico e, em
forma APA-7 já montada, dentro de `scripts/make_apa7_export.py` — que é quem de fato gera o
artigo. Editar só o Markdown canônico **não muda o artefato publicado**, e a primeira tentativa
de inserir o DOI foi silenciosamente perdida por causa disso (o PDF saiu sem o DOI). Quem
alterar referência precisa alterar os dois, ou o export mente sobre a fonte.

## [1.0.0] — 2026-07-30

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
- `REPRODUCIBILITY.md` — o que cada selo prova (dado **externo e fixado** por SHA-256 vs.
  derivação **reproduzível**), o escopo honesto do determinismo (bit-a-bit **na mesma
  plataforma**; entre plataformas o que se afirma são sinais, ordenações e conclusões de
  intervalo), a verificação sem re-rodar nada, e o que não é corrigível dentro do pacote.
- `requirements.lock` — fechamento transitivo completo do ambiente do run selado (31 pacotes),
  gerado **verbatim** de `environment.pip_freeze` no `manifest.json`, sem edição à mão.
- `NOTICE` — atribuição Apache-2.0 §4(d), duplo licenciamento e atribuição do dataset
  ULB/Worldline (não redistribuído).
- `LICENSES/Apache-2.0.txt` (idêntico ao `LICENSE`) e `LICENSES/CC-BY-4.0.txt` — materializam o
  duplo licenciamento que já era declarado nos badges, no README e no texto do artigo.

### Corrigido

- **Vazamento de caminho absoluto no DOCX.** O atributo `descr` da logo da capa carregava o
  caminho do workspace privado. Causa-raiz no gerador (`scripts/make_apa7_export.py`): imagem
  sem *alt text* faz o pandoc escrever o caminho no `descr`, e um segundo `descr`
  (`<pic:cNvPr>`) recebe o caminho mesmo com alt preenchido. Corrigido nas duas pontas — alt
  text em todas as imagens **e** caminho relativo para a logo. Verificado por varredura do
  `.docx` como zip: zero ocorrências de `/Users/` e `research-lab`.
- Badge de testes: `18/18` → **`24/24`** (número real da suíte) — e as **duas menções obsoletas
  a "18 invariants"** que sobraram no corpo do README (*Quick start* e *Layout*), que
  contradiziam o próprio badge.
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
- `scripts/make_run.py` grava o repositório de autoria em `git.repository_url` de forma fixa, de
  modo que o registro selado do run nomeia o repositório privado e o caminho interno onde o
  experimento foi executado em 2026-07-04. É a proveniência literal do selo, preservada como
  está em vez de reescrita depois do fato — reescrever o manifest para esconder onde o trabalho
  foi feito seria adulterar o registro. Do próximo run em diante o campo passa a apontar este
  repositório público.

### Publicação

Push, tag `v1.0.0` e release executados em 2026-07-30 com sign-off do operador. O webhook do
Zenodo cunhou o Version DOI `10.5281/zenodo.21708709` e o Concept DOI
`10.5281/zenodo.21708708`. O artigo desta versão sela com a **URL do repositório** (sem
placeholder de DOI); o DOI entra em metadado não selado na `1.0.1`.
