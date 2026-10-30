# C2 — Teste de poder com sinal plantado (dados de desenvolvimento)

O arquivo `src/nazaret_quant/power.py` acrescenta uma ferramenta **exploratória** de planejamento estatístico: ela não busca oportunidades nem gera decisões de negociação.

## Entrada e unidade

Uma sequência temporal de **diferenças diárias de retorno líquido, pareadas**, em pontos-base (bps), entre uma estratégia previamente definida e seu benchmark no **conjunto de desenvolvimento**. As observações precisam estar ordenadas cronologicamente e igualmente espaçadas por sessão. A série fornecida precisa excluir retornos artificiais, eventos corporativos sem tratamento, sessões ausentes e dados do lockbox.

Para evitar contagem falsa de amostras, a unidade é **sessão/pregão**, não cada operação executada. Se há múltiplos ativos num dia, construir previamente um diferencial de retorno de carteira por sessão; não concatenar cada ativo como observação independente.

## Metodologia

1. Centralizar as diferenças em zero sob hipótese nula.
2. Reamostrar blocos contíguos *sem recombinar artificialmente as duas extremidades* e estimar o quantil do módulo da média.
3. Aplicar o corte bicaudal com Bonferroni para número explícito de comparações.
4. Reamostrar uma segunda distribuição independente e **injetar** efeitos líquidos de tamanho conhecido em bps.
5. Estimar a frequência com que o teste rejeita a hipótese nula e um intervalo de Monte Carlo de 95% (Wilson).
6. Reportar se a **banda inferior** do poder simulado supera o objetivo informado. Isso é uma estatística de desenho experimental, não um portão G2 aprovado.

## Exemplo com dados 100% sintéticos

```python
import numpy as np
from nazaret_quant.power import planted_block_power

serie_sintetica = np.random.default_rng(1).normal(0, 30, 250)
resultado = planted_block_power(
    serie_sintetica,
    effects_bps=[0.0, 5.0, 10.0],
    block_size=5,
    repetitions=2000,
    comparisons=4,
    desired_power=0.8,
)
print(resultado["status"])
for linha in resultado["planted_results"]:
    print(linha["planted_effect_bps_per_session"], linha["estimated_power"])
```

## Limitações obrigatórias

- O deslocamento injetado é artificial e **não demonstra alfa real**.
- Depende de estacionariedade aproximada da estrutura de blocos. Não representa quebras de regime, clusters de ativos, múltiplas estratégias selecionadas a posteriori ou custos não observados.
- Bonferroni aqui corrige somente o **número declarado** de comparações, e não a busca irrestrita de modelos, ativos e parâmetros.
- Retornos de engenharia não ajustados da B3 **não estão autorizados** como entrada de decisão de investimento.
- O retorno é marcado `EXPLORATORY_DESIGN_ONLY_INCONCLUSIVE`; nenhuma autorização de ordens reais, escolha de estratégia ou desbloqueio do histórico de 2026 é produzido.

A funcionalidade precisa ser integrada à futura comparação econômica H2 somente depois de tratar eventos corporativos, custos comprovados, calendário e período de desenvolvimento. Por enquanto, é uma ferramenta independente com testes sintéticos.
