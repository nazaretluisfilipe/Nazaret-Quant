# Relatório de implementação

Data: 30/10/2026. Referência: Plano Diretor Final 1.3 anexado pelo proprietário.

O Nazaret Quant foi iniciado como software executável de pesquisa offline. O núcleo importa e congela dados, simula compras e vendas long-only, confere caixa/posições e gera relatórios com rastreabilidade. Não foi iniciado treinamento de modelos, não foi contatada uma corretora e não há estratégia validada.

## Entregas por ciclo

| Ciclo do plano | Estado desta entrega | Evidência ou impedimento |
|---|---|---|
| C0 Viabilidade | Parcial, REQUER DADOS | Matriz de evidências, política de confirmação e cenários de custos documentados; sem base licenciada e sem corretora identificada |
| C1 Núcleo | Implementado no escopo intradiário descrito | Pacote Python, ingestão CSV/Parquet, validação de qualidade, DuckDB, ledger, motor e 48 testes aprovados |
| C2 Pesquisa | Ferramentas iniciais implementadas | Baselines de engenharia, custos aproximados, MDE normal, bootstrap em blocos, corte purgado e registro de tentativas |
| C2 Validação completa | Pendente | Aleatório pareado, poder por sinal plantado, walk-forward completo e múltiplos testes ainda não implementados |
| C3 Modelos | Condicionado e não iniciado | Nenhum baseline validado com dados reais |
| C4 Execução | Bloqueado | G2 e G3 não aprovados; sem Sentinel operacional, isolamento de processos ou adaptador de broker |
| C5 Piloto | Bloqueado | G0–G6 não aprovados |

## Evidência técnica

A suíte local pytest aprovou 48 testes. O arquivo `reports/pytest-results.xml` registra o resultado. Os casos cobrem contabilidade de compra/venda com taxas, insuficiência de caixa, proibição de short, quantidades inválidas, valores não finitos, duplicidade de IDs, corrupção contábil, timestamps e sessões, duplicatas de dados, snapshots alterados, bloqueio do lockbox e execução causal na próxima barra.

Também foram testados reserva após custos, perda em gap além do gatilho, bloqueio diário após recuperação, saída não executada por volume zero, ausência de liquidação fictícia na última barra, descarte de sinal vencido, overnight, saída parcial, exposição agregada entre ativos, alinhamento da grade temporal, seed determinística, purga/embargo, bootstrap reproduzível e preservação de experimentos que falham.

O teste completo gera preços sintéticos, importa-os em Parquet, executa o motor, cria relatórios HTML/CSV/JSON e registra a tentativa no SQLite. A demonstração entregue contém quatro baselines. Os resultados numéricos não foram usados para selecionar estratégia.

Uma falha inicial na instrução SQL de gravação do registro foi encontrada pela suíte e corrigida. A revisão posterior também incluiu limite de participação na barra de entrada executada, com teste específico, e removeu um parâmetro opcional de abertura de partições no carregador. Não há falha conhecida remanescente nesses 48 testes. Isso não cobre todos os cenários de mercado ou os testes operacionais E4–E6 do plano.

## Limites materiais

O MVP aceita cinco minutos no motor e ainda não trata ações corporativas, calendário oficial, leilões, tick mínimo, livro de ofertas ou histórico point-in-time. A liquidez da execução tem aproximações ex post explicitadas no README; portanto, este motor ainda não constitui evidência suficiente para G2. A marcação de posições abertas é mostrada separadamente do caixa. Não há tributação, custo de oportunidade ou estudo econômico anual implementados.

O registro de hashes e as restrições de arquivos são locais e não representam isolamento de segurança. A confirmação final é bloqueada na CLI, mas deve ser custodiada externamente antes de um estudo real. Nenhuma licença de mercado ou capacidade de corretora foi presumida.

O script de inicialização Windows foi preparado, mas a execução nativa em Windows não foi testada neste ambiente Linux. A suíte Python e a CLI foram executadas aqui. A configuração de GitHub Actions foi escrita, mas não executada remotamente.

## Portões

| Portão | Estado |
|---|---|
| G0 Dados | REQUER DADOS |
| G1 Custos e poder | INCONCLUSIVO |
| G2 Ciência | NÃO AVALIADO |
| G3 Economia | NÃO AVALIADO |
| G4 Segurança operacional | BLOQUEADO |
| G5 Prospectivo | NÃO INICIADO |
| G6 Ativação de capital | BLOQUEADO |

Não houve contratação, assinatura, depósito, envio de ordens, publicação de serviço ou alteração patrimonial. R$ 250 é somente o limite preliminar modelado na simulação.
