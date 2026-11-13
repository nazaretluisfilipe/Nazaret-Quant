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

## Fila priorizada para o agente GitHub Actions (30/10/2026)

Esta fila transforma a Issue #1 em trabalhos **offline**, executáveis sem arquivos B3 no GitHub e sem intervenção no computador. O agente deve escolher a primeira melhoria pequena ainda não implementada, ler os testes correspondentes, propor no máximo dois arquivos por ciclo, respeitar a versão principal e **não alterar as regras de risco e os bloqueios de negociação real**.

1. **B3 — validação determinística (C1):** ampliar testes para comprimento de registro, datas inválidas, duplicações, conversão de centavos, campos numéricos, tipos de mercado e coerência OHLC; evitar testes redundantes. Correções somente se comprovadas por fixture controlada e pelo layout existente. Não inventar interpretação para as 59 exceções reais.
2. **Qualidade e rastreabilidade (C1):** testar que erros de leitura não são silenciosos, estatísticas de rejeição se reconciliam, dados originais são imutáveis e operações diárias não são confundidas com candles de cinco minutos.
3. **Estatística exploratória (C2):** fortalecer testes do MDE aproximado, bootstrap em blocos e corte temporal purgado, inclusive dados inválidos, dependência, seeds e limites explícitos. Não atribuir significância econômica a resultados de fixtures.
4. **H2 e eventos corporativos (preparação, não backtest):** implementar apenas contratos de dados, validações ou módulos puros com dados artificiais, com falha segura na ausência de eventos/calendário autorizados. Sem estimar retornos reais ou ajustar histórico por suposição.
5. **Documentação de pendências:** registrar impedimentos que dependem do fornecedor, corretora ou acesso ao arquivo B3. Não marcar como concluído algo não validado.

**Critério de avanço:** se o item anterior já estiver coberto no código, passar ao próximo; não editar arquivos apenas para produzir commits. Um ciclo que não encontra mudança segura pode terminar sem alterações. Cada mudança deve passar na suíte completa; a `main` não será atualizada automaticamente.

**Bloqueios externos permanentes:** falta a verificação da licença dos dados; faltam eventos corporativos, calendário oficial, spread negociável, tarifas confirmadas, fonte intradiária H1, histórico longo H2, custódia de lockbox e autorização específica para ordens reais. Essas lacunas não podem ser resolvidas inventando valores, aproximando mercado fracionário pelo padrão ou consultando 2026.
