# Protocolo C2: validação walk-forward com purga temporal

**Estado:** utilitário técnico de desenho de validação; não é estimativa de alfa, backtest ou decisão de negociação. O módulo `nazaret_quant.walk_forward` calcula cortes cronológicos estritamente *forward-only* sobre observações já normalizadas.

## Contrato de entrada

Cada registro contém `(feature_time, label_end, session)`. Os dois tempos precisam ser `datetime` com timezone, em ordem cronológica, e `session` é a data local brasileira `YYYY-MM-DD`. Vários ativos podem compartilhar uma data e timestamp. A função não adivinha o fim de cada label.

O chamador informa: mínimo de sessões de treino, janela de validação (em sessões observadas), passo da janela, intervalo de separação pré-validação e tamanho máximo opcional de janela móvel de treino. O sistema não possui acesso a dados de mercado: a execução e os testes usam datas artificiais.

**O módulo não verifica se as sessões informadas são de fato pregões da B3.** Antes de um estudo real, a fonte licenciada de calendário e a identidade/tempo das ações devem ser confirmadas. Sessões ausentes nos dados não são preenchidas automaticamente.

## Proteção contra vazamento

- A validação vem apenas depois do treino; nenhum exemplo posterior à validação é reutilizado no treino.
- Um exemplo só pode entrar no treino se seu `label_end` for *estritamente anterior* à primeira observação da janela de validação.
- Remove um intervalo configurável de sessões imediatamente anterior à validação; isso não substitui a purga dos labels.
- Se restar um número de sessões de treino inferior ao mínimo após a purga, a janela é descartada e **contabilizada** em `skipped_folds_due_to_purging`. Se nenhuma janela sobreviver, o programa falha explicitamente.
- O número de janelas por execução é limitado para evitar busca computacional irrestrita.
- Datas de ativos não representam observações estatisticamente independentes; as inferências precisarão considerar correlação temporal e entre ativos.

## Exemplo apenas com datas fictícias

```python
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from nazaret_quant.walk_forward import purged_walk_forward

tz = ZoneInfo("America/Sao_Paulo")
base = datetime(2025, 1, 6, 10, tzinfo=tz)
obs = [(base + timedelta(days=i), base + timedelta(days=i+2),
        (base + timedelta(days=i)).date().isoformat()) for i in range(45)]
result = purged_walk_forward(obs, min_train_sessions=10, validation_sessions=5,
                             gap_sessions=1)
print(result["status"], len(result["folds"]))
```

Este exemplo usa dias civis, **não calendário oficial de pregões**. Não usar os resultados para inferências econômicas. Antes de G2, ainda são necessários universo histórico, custos demonstrados, proventos, metodologia de comparação, correção por seleção de modelos, experimentos em múltiplos períodos e custódia do lockbox de 2026.

Código sem chamadas à corretora ou aos arquivos de 2026. A `main` exige revisão e autorização explícitas antes de incorporar esta alteração.
