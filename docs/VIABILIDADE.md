# Viabilidade e evidências pendentes

O planejamento é a referência de requisitos, não evidência de que uma rota de negociação esteja disponível para esta conta. As consultas externas tentadas nesta sessão não retornaram conteúdo. Assim, nenhuma tarifa, disponibilidade de fracionário, API, licença ou condição comercial foi revalidada independentemente nesta entrega. Os endereços a seguir foram preservados a partir do plano e servem apenas como pontos de consulta futura.

| Rota citada no plano | Evidência disponível agora | Pendência que impede aprovação |
|---|---|---|
| Corretora com MT5 e integração Python | Documentação de referência indicada no plano; nenhuma corretora informada | Confirmação escrita para conta PF, mercado à vista/fracionário, histórico/licença, consultas/envios/cancelamentos e limites |
| Profit com automação | Candidato descrito no plano; nenhuma contratação ou preço validado | Separar simulação/real, licença e obrigações de volume; conferir mecanismo oficial de integração |
| API B3 | Plano aponta FAQ com restrição B2B | Revalidar conteúdo e viabilidade; não tratar API direta como rota aprovada para PF |
| CSV/Parquet licenciado | Importador implementado e testado com fixtures | Receber fonte, licença de armazenamento/processamento, período e instrumentos de uma base real |

## Evidências a solicitar à corretora

É necessário obter o nome da instituição e a documentação escrita sobre conta PF, ações integralmente pagas, fracionário, ausência de margem/crédito, recursos segregados, risco de encargos adicionais, consulta de saldo/posição/ordens, IDs idempotentes, execução parcial, reconexão, cancelamento, leilões, stops no servidor, limites de taxa e suporte operacional. A confirmação deve incluir custos fixos/variáveis, expiração de gratuidade e eventual obrigação de volume. O projeto não autoriza contratação recorrente.

O orçamento operacional de R$ 250 não equivale a garantia de perda máxima. Só uma rota contratualmente e tecnicamente compatível com o limite pode passar por G4. Um stop local não comprova essa proteção.

## Dados antes dos sinais

Para H1, exigir histórico de cinco minutos com timestamps de abertura/fechamento, timezone, símbolos corretos, lacunas e volume em ações. Bid/ask ou negócios licenciados são necessários para calibrar a execução; OHLCV do lote padrão não certifica o fracionário. Para H2, exigir preços, proventos, corporativos, calendário e universo histórico. A ausência desses itens deve constar como REQUER DADOS, sem inventar spreads ou histórico.

Antes de abrir retornos condicionais, congelar ativos/períodos, separar exploração/treino/validação/confirmação e registrar a grade de tentativas. Uma base já explorada não volta a ser amostra virgem. O lockbox deve ficar sob custódia independente da pasta acessível ao pesquisador.

## Custos e poder

`config/costs.yaml` contém somente cenários numéricos de engenharia. Não são cotações nem estimativas de mercado obtidas nesta sessão. O mapa de custos soma aproximadamente duas meias diferenças bid/ask, dois slippages, taxas por lado e custos fixos por execução. Não usa custos de um horizonte como requisito automático de outro.

O MDE implementado é uma aproximação normal didática, com número efetivo de observações fornecido como entrada. O estudo definitivo ainda precisa estimar dependência temporal e entre ativos, testar 1/3/14 operações por dia e executar simulações em blocos com sinal plantado. Ausência de poder implica INCONCLUSIVO, não refutação de alfa.

## Endereços de referência do plano

- B3 FAQ: https://developers.b3.com.br/faq
- Integração Python MT5: https://www.mql5.com/en/docs/python_metatrader5
- Histórico MT5: https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesfrom_py
- Nelogica automação: https://ajuda.nelogica.com.br/hc/pt-br/articles/8864900151451-Como-contratar-o-m%C3%B3dulo-Automa%C3%A7%C3%A3o-de-Estrat%C3%A9gias

Tributação e tarifas vigentes não foram incorporadas como regras fixas no código. Devem ser verificadas em fontes oficiais antes de G3.
