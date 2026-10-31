# Expectância, drawdown e sizing por stop — protocolo conservador

Este módulo fornece *diagnósticos descritivos e hipotéticos*; não envia ordens, não acessa histórico 2026, não seleciona estratégias e não desbloqueia G2/G3/G6.

## Expectância de operações encerradas

\`E[P&L] = P(ganho)*ganho_médio - P(perda)*perda_média\`.

Entradas: resultados líquidos em R$ de **posições integralmente encerradas**. Taxas, spread, slippage, eventos corporativos aplicáveis e impostos precisam ser refletidos antes de alimentá-lo. Não se deve contar **cada fill** como um trade independente: fechamentos parciais e ordens divididas precisam ser agregados pelo ledger. Resultados exatamente zerados entram no denominador, não como vencedores nem perdedores. A fórmula é uma descrição histórica e **não prevê retornos futuros**.

O resultado não inclui intervalo de confiança, dependência temporal, correção por seleção de modelos, variação de regime, custos de oportunidade ou testes fora da amostra. Sem essas camadas, mesmo uma expectância observada positiva permanece cientificamente inconclusiva.

## Drawdown

Medir queda do **patrimônio marcado** do pico histórico até o vale, incluindo o capital inicial e posições ainda abertas. Não confundir com perda realizada, perda diária ou limite máximo garantido. Se uma ordem de saída não puder ser preenchida, o drawdown pode exceder qualquer limite planejado.

## Tamanho da posição

Para posição comprada planejada:
- custo estimado de entrada/unidade: preço de entrada + atrito estimado;
- receita estimada de saída/unidade: preço do stop - atrito estimado;
- risco estimado por unidade: diferença entre esses preços;
- orçamento de perda no stop: \`risk_budget\`, incluindo duas comissões fixas;
- orçamento de capital: mínimo entre caixa livre após reserva e exposição disponível, incluindo taxa de compra;
- quantidade: o menor teto inteiro entre restrição de caixa e restrição de risco, respeitando o tamanho de lote.

Essa conta **não cria stop real**, nem limita uma perda em caso de gap, leilão, suspensão, livro vazio ou slippage não observado. Não adaptar o risco por operação para cima após perdas, não aumentar posições perdedoras para "recuperar" e não usar martingale. A função não incorpora histórico de perdas e nunca executa uma ordem.

Exemplo com parâmetros sintéticos:

\`\`\`python
from nazaret_quant.risk_metrics import (
    expectancy_from_closed_trades, maximum_drawdown, size_for_fixed_stop
)
print(expectancy_from_closed_trades([5, -2, 0, 5, -2]))
print(maximum_drawdown([250, 260, 230, 240]))
print(size_for_fixed_stop(entry_price=10, stop_price=9.50,
    cash_available=250, reserve=100, remaining_exposure=150, risk_budget=5))
\`\`\`

## Lacunas de integração a resolver antes de G2

O motor H1 atual dimensiona por **orçamento nocional**, não exige stop operacional. \`size_for_fixed_stop\` fica isolado dele até existir uma semântica testada de execução de stop, gap, barras e custos observáveis. Também falta consolidar os fills do ledger em trades fechados com FIFO/fees, e recalcular expectância líquida e drawdown nos relatórios antes de qualquer conclusão econômica.

**Prioridade científica:** resultados por trade e por sessão (correlação), drawdown e sua distribuição, risco de ruína sob cenários adversos, sensitivity to costs, comparação com benchmark e intervalos de incerteza. O objetivo não é maximizar taxa de acerto isoladamente.
