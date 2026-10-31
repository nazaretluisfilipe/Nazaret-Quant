# C1 — Ingestão e auditoria de vários anos COTAHIST (uso local)

**Objetivo:** permitir ao pesquisador reunir anos de cotações anuais obtidos manualmente e, **antes de qualquer backtest**, produzir um relatório de engenharia que revele anos ausentes, SHA-256, linhas rejeitadas, fatores de cotação e inconsistências. O projeto não faz downloads automáticos da B3 nem publica arquivos de preços.

## Origem dos dados e direitos

Consulte a página oficial da B3: https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/mercado-a-vista/cotacoes-historicas/

A página permite consultar séries desde 1986, mas explicita limitações de uso e veda **coleta automatizada**, inclusive por IA. A análise privada/local e qualquer utilização operacional precisam respeitar os direitos e condições vigentes; **o auditor não certifica licença**.

Para o piloto técnico, a janela sugerida é **2018–2025**; o recorte final de treino/validação deve ser pré-especificado depois da checagem de quantidade de pregões, mudanças de ticker, qualidade de dados, calendário e eventos. **2026 continua intocado como lockbox.** Não envie os ZIPs à API Gemini nem publique esses arquivos no repositório.

## Execução (se os arquivos estiverem disponíveis legitimamente)

Organize arquivos anuais de forma local, por exemplo:

\`\`\`text
dados-locais/b3/COTAHIST_A2018.ZIP
dados-locais/b3/COTAHIST_A2019.ZIP
...
dados-locais/b3/COTAHIST_A2025.ZIP
\`\`\`

Execute em ambiente Python com o pacote instalado:

\`\`\`powershell
python -m nazaret_quant.annual_quality --years 2024,2025 --acquisition-note "Obtido manualmente; verificar termos da B3 para o uso planejado" --report dados-locais/qa_2024_2025.json dados-locais/b3/COTAHIST_A2024.ZIP dados-locais/b3/COTAHIST_A2025.ZIP
\`\`\`

O comando **nunca sobrescreve** um manifesto existente. Para todos os oito anos, explicite \`--years 2018,2019,2020,2021,2022,2023,2024,2025\` e inclua cada ZIP da janela. O relatório registra anos ausentes sem afirmar que o calendário está completo.

## Portão científico G0 não é liberado pela importação

Mesmo com oito ZIPs e testes verdes, a pesquisa H2 precisa ainda de:
- Proventos, grupamentos, desdobramentos e demais eventos **com datas de conhecimento** point-in-time.
- Calendário de pregões oficial, suspensões/alterações de tickers e universo histórico que inclua ativos retirados da bolsa.
- Definição do instrumento operável com R$ 250 e viabilidade fracionária por sessão; liquidez e custo executável.
- Documentação do alcance da licença/uso; metodologia pré-registrada e separação temporal sem abrir 2026.

**Resultados anuais são exclusivamente QA de dados não ajustados.** O auditor não gera sinal, não ajusta retorno, não seleciona ativos, não faz scraping e não envia ordens reais.
