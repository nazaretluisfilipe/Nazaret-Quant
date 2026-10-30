# Nazaret Quant

Núcleo de pesquisa offline 0.1.0 implementado a partir do Plano Diretor Final 1.3, de 30/10/2026. Este pacote importa dados, simula operações compradas integralmente pagas, confere caixa e posições, registra experimentos e produz relatórios locais.

**Estado: pesquisa iniciada; nenhuma estratégia validada; negociação real indisponível.** Os exemplos e os relatórios entregues usam exclusivamente dados sintéticos. Seus valores verificam o funcionamento do programa e não representam rentabilidade esperada.

## Executar no Windows

Requer Python 3.12 ou superior com pip. Extraia todo o ZIP. Abra a pasta `nazaret_quant` e execute `iniciar_demo.bat`. Na primeira execução, o programa cria um ambiente virtual local e instala as dependências de código aberto; isso exige internet. Depois executa os testes e abre o relatório sintético de momentum no navegador. Cada execução recebe uma pasta nova; nada opera em corretora.

Se o Python não estiver disponível, instale-o antes e ative a opção de incluí-lo no PATH. O script não instala Python nem solicita credenciais financeiras. Os relatórios que já estão em `reports/demo` podem ser abertos sem instalar nada.

## Instalação manual

No terminal, dentro desta pasta:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest -q
python -m nazaret_quant.cli demo --output data/minha-demo
```

Abra `data/minha-demo/reports/momentum/report.html`. Para repetir, escolha um nome de saída novo. A CLI também é disponibilizada como `nazaret` após instalação.

## Dados reais

Nenhuma base real foi fornecida ou adquirida. O CSV de exemplo está em `reports/demo/synthetic.csv`. O schema contém:

| Campo | Significado |
|---|---|
| bar_open | Instante de abertura com timezone explícito |
| timestamp | Instante de fechamento com timezone explícito |
| symbol | Instrumento da fonte; o motor não traduz símbolos para corretoras |
| open, high, low, close | Preços positivos da mesma unidade |
| volume | Quantidade de ações, não volume financeiro |
| session | Data do pregão em America/Sao_Paulo, formato YYYY-MM-DD |

O importador aceita CSV/Parquet e dados de qualquer intervalo para inspeção. O motor atual aceita somente barras alinhadas de cinco minutos; **H2 diária/semanal não está implementada**. Proventos, desdobramentos, universo histórico, leilões e calendário da bolsa precisam de tratamento antes de pesquisa científica real.

Crie seu próprio arquivo de proveniência seguindo `examples/provenance.json`. Para dados reais, use `synthetic: false` e registre fornecedor, licença e evidência efetivos. Não reutilize a licença dos exemplos para dados de mercado.

```bash
python -m nazaret_quant.cli ingest meus_precos.csv --provenance minha_proveniencia.json --output data/snapshot-001
python -m nazaret_quant.cli cost-map data/snapshot-001
python -m nazaret_quant.cli backtest data/snapshot-001 --strategy no_trade --experiment EXP-001 --output data/estudo/EXP-001
python -m nazaret_quant.cli backtest data/snapshot-001 --strategy momentum --scenario adverse --experiment EXP-002 --output data/estudo/EXP-002
```

Os snapshots nunca são sobrescritos pelo importador. Alterações nos preços são detectadas pelo hash ao carregar. O manifesto e o banco de experimentos são arquivos locais do pesquisador: não há assinatura externa, armazenamento inviolável nem isolamento de sistema operacional nesta versão.

## Comportamento da simulação

Um sinal usa apenas fechamentos conhecidos e tenta comprar na abertura da próxima barra disponível, respeitando validade temporal. Quantidades são inteiras; o caixa deve cobrir preço e taxas; a reserva de R$ 100 e exposição de entrada de até R$ 150 são aplicadas ao orçamento de R$ 250. A valorização ou um gap podem levar a exposição marcada acima do limite de entrada. A venda tenta ocorrer após 30 minutos, após quebra de sessão, no horário de zeragem configurado ou por gatilho de perda. Não há preenchimento garantido: posições sem liquidez ou sem próxima barra permanecem abertas e geram alertas.

Os horários em `Policy` são **exemplos configuráveis de engenharia, não o calendário oficial da B3**. Os gatilhos de R$ 5/dia e R$ 20 acumulados bloqueiam novas compras e pedem saída na próxima abertura; não impõem perda máxima. O motor registra perdas que ultrapassam esses valores em gaps.

Custos são separados em meio spread por lado, slippage por lado, taxa proporcional e tarifa fixa por execução. O preço de referência é ajustado pelo spread/slippage uma vez, e as taxas são debitadas à parte. Os cenários `base` e `adverse` de `config/costs.yaml` são **hipóteses não confirmadas**. Dinheiro é conciliado em centavos; preços de execução conservam precisão decimal e não simulam o tick de uma corretora.

OHLCV é insuficiente para reconstruir o book. A simulação usa a abertura como proxy agressora e o volume da barra executada como veto/limite ex post de liquidez. Esse volume nunca entra na previsão de sinal; ainda assim, a aproximação de execução impede usar esta versão como validação final de alfa. Na entrada, o dimensionamento usa o volume da barra já conhecida. Não há modelo de fila, bid/ask observado, leilão ou impacto calibrado. A ordenação de ativos é determinística por símbolo e não é uma política ótima de carteira.

O ledger contém caixa, posições, execuções com IDs únicos e partidas balanceadas de caixa/títulos/taxas, reconciliadas após cada execução. É contabilidade de simulação, não escrituração fiscal ou OMS completo. Ordens limitadas, cancelamentos concorrentes, conectividade, execução real parcial e reconciliação com broker pertencem à fase operacional futura.

## Pesquisa e governança

`no_trade`, `momentum`, `reversal` e `random` são baselines de engenharia. O aleatório é reproduzível por seed, mas **ainda não é pareado por frequência/risco**. As hipóteses H1-M, H1-R, H2-R e H2-T permanecem rascunhos; não há modelo treinado nem vantagem comprovada.

`research.py` oferece mapa aproximado de custos, MDE normal didático, bootstrap em blocos móveis e um corte temporal com purga/embargo. Esses utilitários não equivalem ao protocolo definitivo de poder com sinal plantado, walk-forward completo, teste pareado, correção de seleção/múltiplos testes, tributação ou viabilidade econômica anual.

Antes de acessar retornos de cada simulação, a CLI grava ID, seed, parâmetros, configuração, período e hashes no SQLite. A conclusão ou falha é anexada sem apagar tentativas. A cadeia de hashes detecta alterações casuais; um usuário com controle completo dos arquivos pode reescrevê-la. A CLI registra testes exploratórios e não fornece acesso ao lockbox, mesmo que o usuário tente selecioná-lo. A proteção é lógica, **não uma barreira de segurança contra alguém com acesso aos dados**. O lockbox real deverá ficar sob custódia independente.

Todas as execuções nesta versão recebem parecer `INCONCLUSIVE`. Os portões G2/G3 não são avaliados automaticamente. Não há comando que permita ativar ordens reais.

## Entregas e próximos passos

Consulte `docs/STATUS.md` para o que foi implementado, `docs/VIABILIDADE.md` para evidências pendentes e `docs/CONTINUIDADE.md` para a ordem da próxima execução. O pacote inclui testes, relatórios HTML/CSV/JSON e o registro sintético de tentativas. A automação GitHub Actions está preparada; só foi validada localmente, pois não houve envio a um repositório remoto.

O próximo insumo necessário é uma base de dados com licença e proveniência verificáveis. Uma corretora é necessária para estudar a rota operacional; sua ausência não impede a pesquisa offline. Não envie senhas ou tokens no chat.
