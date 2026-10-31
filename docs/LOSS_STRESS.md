# C2 — Estresse determinístico de perdas e limites (sem probabilidade de ruína)

\`nazaret_quant.loss_stress.loss_streak_stress\` testa uma sequência artificial de perdas, sua multiplicação por gaps hipotéticos e os controles de interrupção. **Não estima a probabilidade estatística de ruína**, não prediz distribuição de retornos e não envia ordens.

Entradas: capital e reserva, risco nominal constante em reais por tentativa, gatilhos de perda diária e acumulada e uma lista ordenada de \`(sessão, multiplicador_de_perda)\`. Os multiplicadores são cenários escolhidos pelo pesquisador (não distribuições observadas). A perda projetada é \`risco_fixo × multiplicador\`, limitada neste modelo sem alavancagem ao patrimônio restante.

O risco nominal nunca sobe após perdas. Dentro da mesma sessão o gatilho diário fica travado; em uma nova sessão ele reinicia somente se o gatilho acumulado não bloqueou o sistema. Gatilhos são avaliados **depois** do resultado, portanto um gap pode ultrapassar simultaneamente perda diária, perda total e reserva: **não são garantias**.

Exemplo fictício:

\`\`\`python
from nazaret_quant.loss_stress import loss_streak_stress

report = loss_streak_stress(
    capital=250, reserve=100, fixed_risk_per_attempt=2,
    daily_loss_trigger=5, total_loss_trigger=20,
    scenarios=[("dia-1", 1), ("dia-1", 1), ("dia-1", 3),
               ("dia-2", 1), ("dia-3", 1)])
print(report["status"], report["executed_attempts"])
\`\`\`

Para estimar de forma científica risco de ruína, seriam necessárias probabilidades condicionais de ganho/perda, dependência temporal, caudas, regime, liquidez e calibração *fora da amostra*; não há base para inserir números arbitrários. O teste serve para verificar se a política desenhada é estruturalmente frágil, não para certificar sobrevivência em mercado real.
