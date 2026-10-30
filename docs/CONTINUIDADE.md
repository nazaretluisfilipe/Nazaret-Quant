# Continuidade da execução

A próxima etapa depende de dados históricos autorizados. O código e os relatórios sintéticos já permitem verificar funcionamento, mas não decidem rentabilidade.

1. Identificar a fonte e a licença de uma base real; receber metadados sem credenciais. Confirmar unidade de volume, timezone, mercado, períodos, lacunas e se os preços sofreram ajustes.
2. Concluir G0 por hipótese. Se não houver dados adequados a H1, avaliar H2 separadamente, implementando primeiro corporativos e calendário; não simular essas informações.
3. Concluir Fase A em exploração: calibrar custos com evidência observável e viabilidade de quantidades inteiras. Examinar dados ausentes sem procurar sinais na confirmação.
4. Congelar `hypotheses.yaml` com universo, períodos, hipóteses operacionalizadas, métricas primárias, grade finita, contagem de tentativas e regra de decisão. Custodiar o lockbox fora do acesso de desenvolvimento.
5. Completar C2: aleatório pareado, validação walk-forward, comparação pareada, dependência temporal, poder por sinal plantado e correção de seleção/múltiplos testes. Endurecer o simulador de execução e submeter os pressupostos à revisão independente.
6. Executar baselines em treino/validação. Se os critérios pré-fixados justificarem, acrescentar regressão regularizada; modelos adicionais só conforme o plano. Não procurar lucro por busca irrestrita de variantes.
7. Implementar tributação separada, cenários de custo fixo, custo de oportunidade comparável e margem de segurança; decidir G2/G3 por hipótese/rota com incerteza.
8. Somente após G2+G3, projetar e testar Sentinel/Execution isolados, reconciliação de broker e falhas E4–E6. Em seguida coletar evidência prospectiva de modelo congelado.
9. Piloto real apenas após G0–G6 e autorização expressa específica de ativação e orçamento.

Nenhuma dessas etapas requer enviar senha, cookie ou token de corretora no chat. Qualquer integração futura deve manter credenciais fora do ambiente de pesquisa.
