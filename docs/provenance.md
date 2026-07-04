# Proveniência — por que este repositório reanalisa material precedente

Este pacote de replicação acompanha o paper *Ponto de operação, protocolo e a fragilidade
do ranking de arquiteturas na detecção de fraude em cartões* (Flores, 2026), que reanalisa
material precedente **não publicado** do próprio autor: um relatório técnico e um caderno
computacional de agosto de 2025 (v3.2).

## O material arquivístico

- `docs/source/estudo_caso_fraude_cartao_pytorch_v3p2_final_full.ipynb`
- SHA-256: `131b5af0ba04c6456ddf9229c6972b43a1539777512d4edbdac4ae9af292c039`
- O SHA-256 do dataset registrado por aquela execução
  (`76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89`) é o mesmo
  verificado por `scripts/get_data.py` — a cadeia de dados é idêntica bit a bit.

## Reconciliação texto↔código (resumo)

A comparação entre a prosa do relatório precedente e o código que o caderno executa
revelou divergências materiais, todas documentadas e corrigidas no paper:

| Prosa precedente afirmava | O código v3.2 executa |
|---|---|
| Sobreamostragem SMOTE no treino | Nenhum oversampling; reponderação de custo (`pos_weight≈578,5`; `class_weight="balanced"`) |
| Calibração Platt / temperature scaling | Nenhuma calibração; pontuações ordinais |
| Arquitetura 30-16-8-2 com Cross-Entropy | 30-64-32-1 com BatchNorm e BCE ponderada |
| Estabilidade de F1 sob prior-shift 1–20% | O teste nunca atingia as prevalências nominais (defeito `min(n_pos, 74)`; prevalência efetiva ~0,2%) — replay forense em `scripts/verify_original_priorshift_bug.py` |

O paper descreve exclusivamente o que o código executa; a decisão editorial, o método da
reconciliação e a leitura dos dois artefatos de protocolo encontrados (a censura da grade
de limiares e o defeito do prior-shift) estão nas Seções 4, 6.2, 6.5 e 8 do paper.

## Escopo da alegação de reprodutibilidade

Determinística de código→dados→resultados na plataforma documentada (duas execuções
completas idênticas em todos os blocos; manifest + SHA-256 por artefato em `runs/`).
A variação entre plataformas/sementes não é ruído a esconder: é um dos resultados do
paper (Seção 6.3).
