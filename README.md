# Operating-Point Dominance in Credit-Card Fraud Detection

<!-- DOI Zenodo: inserir o badge após o mint (Wave 2) -->
<!-- [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.TBD.svg)](https://doi.org/10.5281/zenodo.TBD) -->
[![License: Apache-2.0](https://img.shields.io/badge/code-Apache--2.0-blue.svg)](LICENSE)
[![License: CC BY 4.0](https://img.shields.io/badge/content-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-18%2F18-brightgreen.svg)](tests/)

*Estudo de caso confirmatório e auditável no benchmark ULB/Worldline: quanto do desempenho
operacional de um detector de fraude vem da arquitetura — e quanto vem do ponto de operação.*

**Paper (PT-BR):** [`docs/paper/paper-final.md`](docs/paper/paper-final.md) ·
**Auditoria de qualidade:** [`docs/paper/AUDIT-2026-07-04.md`](docs/paper/AUDIT-2026-07-04.md) ·
**Proveniência:** [`docs/provenance.md`](docs/provenance.md)

## What this contributes

1. **Decomposição auditável dos efeitos.** Com bootstrap pareado (10.000 réplicas) e um
   estudo de variância de treino (20 sementes), mede-se que mover o limiar de decisão do
   MLP de 0,5 para o ótimo de validação (τ*=0,9994) desloca o F1 de teste em **+0,545**
   (0,267 → 0,812), enquanto trocar MLP por Regressão Logística desloca **−0,007**
   (IC 95% [−0,055; +0,042]) — menor que o desvio-padrão de treino do próprio MLP (0,016).
2. **Forense de protocolo.** Uma aparente vitória do MLP com significância
   (ΔF1 = +0,053, IC excluindo zero) é demonstrada como **artefato da grade de limiares
   truncada em 0,99** herdada do material precedente; e o teste de prior-shift original é
   refutado (defeito de reamostragem travava a prevalência efetiva em ~0,2%).
3. **Protocolo sem vazamento de pré-processamento, reproduzível bit a bit:** scaler
   ajustado só no treino, reponderação de custo (sem oversampling sintético), limiar
   selecionado só em validação, dados ancorados por SHA-256, determinismo verificado por
   re-execução idêntica e invariantes cobertos por testes.

## Model at a glance

| Item | Valor |
|---|---|
| Dataset | ULB/Worldline `creditcard.csv` (284.807 transações; 0,173% fraudes; SHA-256 `76274b69…a89`) |
| Partição | 70/15/15 estratificada, semente 42 (199.364 / 42.721 / 42.722) |
| Modelos | MLP 30-64-32-1 (BatchNorm, Dropout 0,2, pos_weight≈578,5) · LR balanced · Autoencoder · Isolation Forest |
| Seleção de limiar | validação apenas; dois regimes reportados (grade v3.2 censurada + curva PR sem censura) |
| Inferência | bootstrap pareado 10.000×; multi-seed 20×; forma fechada prec(π) para prior-shift |
| Determinismo | thread única + algoritmos determinísticos; 2 runs completos idênticos |

## Quick start

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run_all.py            # baixa+verifica dados, roda o experimento, figuras, manifest
pytest tests/ -q             # 18 invariantes de dados/protocolo/resultados
```

## Five-step replication protocol

1. `python scripts/get_data.py` — baixa `creditcard.csv` (mirror público) e **verifica o
   SHA-256** contra o hash do estudo original; aborta em divergência.
2. `python scripts/run_experiment.py` — protocolo completo (4 modelos, 2 regimes de limiar,
   bootstrap pareado, prior-shift em forma fechada) → `output/results.json`.
3. `python scripts/verify_original_priorshift_bug.py` — replay forense das duas variantes do
   stress test (defeituosa vs corrigida) sobre as pontuações salvas.
4. `python scripts/multiseed_mlp.py --n-seeds 20` — variância de treino do MLP
   (~25 min CPU) → `output/multiseed_mlp.json`.
5. `python scripts/make_figures.py && (cd scripts && python make_run.py)` — figuras
   vetoriais (PDF+SVG) e o contrato de run (`runs/<id>/manifest.json` + `checksums.sha256`).

Re-executar os passos 2–5 na mesma plataforma reproduz todos os números bit a bit
(verificado em duas execuções completas independentes).

## Results (seed 42, test split)

| Modelo @ limiar | Precisão | Revocação | F1 |
|---|---|---|---|
| MLP @ 0,50 (default) | 0,157 | 0,878 | 0,267 |
| MLP @ τ*=0,9994 | 0,875 | 0,757 | **0,812** |
| LR @ τ*≈1,0 | 0,931 | 0,730 | **0,818** |
| Autoencoder @ F1-ótimo | 0,769 | 0,405 | 0,531 |
| Isolation Forest @ F1-ótimo | 0,112 | 0,459 | 0,179 |

ΔF1(MLP−LR) = −0,007 [−0,055; +0,042]; ΔAUC-PR = −0,046 [−0,111; +0,005] — ambos
indistinguíveis de zero. MLP sobre 20 sementes: 0,814 ± 0,016 (a LR determinística cai
dentro da distribuição do MLP). Números completos em [`output/results.json`](output/results.json).

## Layout

```
docs/paper/       paper-final.md (com figuras) + AUDIT (rubrica 966/1000)
docs/source/      notebook arquivístico v3.2 do estudo precedente (SHA-256 131b5af0…)
docs/provenance.md  reconciliação texto↔código do material precedente
configs/run.json  todos os hiperparâmetros e contratos do protocolo
scripts/          experimento, multiseed, forense, figuras, manifest, hashing
tests/            18 invariantes (dados, protocolo anti-vazamento, resultados)
output/           results.json, scores brutos (npz), tabelas CSV, figuras PDF+SVG+PNG
runs/<id>/        manifest.json + checksums.sha256 (contrato de run audit-grade)
schema/           schemas do manifest e do dataset
```

## Documentation

- [`docs/provenance.md`](docs/provenance.md) — por que este repo reanalisa (e corrige) o
  material precedente do próprio autor; o notebook original acompanha como material
  arquivístico com hash.
- [`docs/paper/AUDIT-2026-07-04.md`](docs/paper/AUDIT-2026-07-04.md) — auditoria de
  qualidade (estrutura, densidade, fundamentação, originalidade, consistência, correção
  factual) com evidência por sub-critério.

## Citation

<!-- Após o mint do DOI no Zenodo, atualizar CITATION.cff e o BibTeX abaixo. -->

```bibtex
@misc{flores2026operatingpoint,
  author = {Flores, Carlos Ulisses},
  title  = {Ponto de opera{\c c}{\~a}o, protocolo e a fragilidade do ranking de
            arquiteturas na detec{\c c}{\~a}o de fraude em cart{\~o}es},
  year   = {2026},
  note   = {Codex Hash Research Laboratory. DOI Zenodo a ser cunhado},
}
```

Metadados machine-readable: [`CITATION.cff`](CITATION.cff) · [`codemeta.json`](codemeta.json) ·
[`.zenodo.json`](.zenodo.json).

## License

- **Código** (`scripts/`, `tests/`, `run_all.py`): [Apache-2.0](LICENSE)
- **Conteúdo** (paper, figuras, documentação): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

## Anchor references

- Hayat & Magnier (2025). *Data leakage and deceptive performance…* — 10.3390/math13162563
- Abdelhamid & Desai (2024). *Balancing the scales…* — arXiv:2409.19751
- van den Goorbergh et al. (2022). *The harm of class imbalance corrections…* — 10.1093/jamia/ocac093
- Hand (2006). *Classifier technology and the illusion of progress* — 10.1214/088342306000000060
- Bouthillier et al. (2021). *Accounting for variance in ML benchmarks* — arXiv:2103.03098

## Contact

Carlos Ulisses Flores · Codex Hash Research Laboratory ·
ORCID [0000-0002-6034-7765](https://orcid.org/0000-0002-6034-7765) ·
[ulissesflores.com](https://ulissesflores.com)
