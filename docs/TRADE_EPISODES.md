# Reconstrução conservadora de operações encerradas

\`trade_analytics.reconstruct_closed_episodes\` consolida os preenchimentos (fills) do simulador, agrupados por símbolo entre estoque zero -> estoque positivo -> retorno a zero.

**Não contabiliza cada venda parcial como um trade independente.** A operação só entra na expectância descritiva depois de completamente encerrada. Todas as taxas estimadas de compra e venda dentro do episódio são descontadas uma vez. As posições abertas são reportadas em separado; o valor marcado aparece na curva patrimonial, não como lucro fechado.

A métrica gerada é \`pnl_after_estimated_costs_before_tax_brl\`. Não há tributos calculados e os preços são aproximações de execução, portanto **não é rentabilidade líquida real**. O relatório deve exibir o estado \`SIMULATION_ACCOUNTING_ONLY_PRETAX_UNCONFIRMED_COSTS\` e não liberar portões científicos, ordens ou novas estratégias.

Exemplos:

- Compra 10 a R$ 10, taxa R$ 1; venda parcial de 4 a R$ 11, taxa R$ 0,40; venda de 6 a R$ 12, taxa R$ 0,60. Resultado de uma **única** operação encerrada: R$ 14 antes de impostos.
- Compra 10 a R$ 10 e vende apenas 4: **nenhum trade encerrado**. O restante deve continuar na categoria de exposição aberta, mesmo com ganhos marcados.

Limitações para futura pesquisa: o método é por **episódio de posição**, não por lote fiscal FIFO; ordens sobrepostas e recompras antes de encerrar uma posição pertencem ao mesmo episódio; podem existir correlação entre símbolos, custos incertos, eventos corporativos e posições ainda abertas. Nenhuma inferência estatística independente decorre das observações de trades.

A análise não inclui martingale nem modifica o motor H1. Dimensionamento por stop exige implementação e validação separadas de ordens de saída, gaps e execução.
