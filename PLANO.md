# LATS 2027 — plano e estado (pasta `lats/`)

Atualizado em 2026-11-23 (sessão Claude Code; autoria definida, título e resumo revistos; parecer de revisão aplicado, ver abaixo). Prazos: **título + resumo 23/11/2026**,
**artigo completo 30/11/2026**. LATS 2027: 13–16/04/2027, Lima. O site oficial só carrega com
JavaScript: **limite de páginas e revisão cega não confirmados** (o rascunho supõe IEEE conference,
até 6 páginas; com os dados da bancada de 23/11 ocupa as 6 páginas inteiras, com poucas linhas de folga).

Artigo: [`paper/main.pdf`](paper/main.pdf) — *How Far from Failure Is a Zero Slack Reading?
Predicting and Guard-Banding the Offset of an FPGA Aging Sensor* (título e resumo novos em 23/11). Texto para o formulário de
título e resumo: [`paper/SUBMISSAO_titulo_resumo.txt`](paper/SUBMISSAO_titulo_resumo.txt).

**Autores (ordem definida em 21/11):** Arthur Pamplona, Danilo Alencar, Alisson Barros, Lucas
Nogueira, Jarbas Silveira (UFC) e Fabian Vargas (IHP). A lista e as afiliações também estão no
arquivo de submissão; o formulário vai pedir os e-mails.

Repositório (privado): `github.com/ArthurPamplonaEng/Lats2027Slack`. A `.venv` não é versionada
(recriar com `requirements.txt`); o README descreve a estrutura, os dados e como reproduzir.

## O que havia nesta máquina

| Item | Situação |
|---|---|
| FPGA no USB | **AU15P placa B** (DNA `…020285`, JTAG FT232H "0ABC01", porta USB 5-3), não a Nexys4. Subia o design da flash (VIO alheio, USR_ACCESS 0). SYSMON lê ~97 °C em ambiente (defeito conhecido do sensor da placa B: a corrente baixa, ~0,37 A, mostra que o die não está a 97 °C). |
| ST-Link | `/dev/ttyACM1`, firmware `$TEL` (latch-up do RCROC), 125 000 baud; Vcore pelo `FUNC_V` (10 mV). |
| Arduino Nano 33 IoT | `/dev/ttyACM0`, **não responde** a nenhum comando do PID do forno em nenhuma taxa: está com outro firmware. Não foi regravado. Sem forno, não houve eixo de temperatura. |
| RTL multi-tap da Nexys4 (HANDOFF) | **não existe aqui** (nunca foi para o `origin/LATS-2027`). |
| Dados AU15P antigos e Run 1 | recuperados da lixeira e do git (ver `README.md`). |
| LaTeX | instalado TinyTeX no usuário (`~/.local/opt/tinytex`), sem sudo. |

## O que foi feito

1. **Sugestões 1–4 da conversa (texto):** nada do SBCCI 2025 é reapresentado como novo (a cadeia de
   inversores, a Tabela I e o resumo saíram; o sensor é citado); unidades em contagens e ps com o
   passo certo (17,857 ps na Nexys4); 214,6 h; VCCINT do XADC (não a tensão da PSU); física da
   temperatura corrigida (inversão perto de 1,0 V); Wong 2009, Stott 2010, Valdés-Peña, Levine 2014,
   FODM (Jiang 2022) e Martins 2011 citados; sobre-estresse e placa única declarados. **O D&T não é
   citado** (pedido de 20/11): a análise de deriva in situ da Run 1 simplesmente não entra.
   Referências conferidas no Crossref.
2. **Sugestão 5 / ideia central (bancada), portada para a AU15P:** projeto novo `hw/au15p_tap`
   (cadeia ripple de 160 LUTs, 23 derivações, sensor + verificador de erro por derivação, varredura
   contínua, estatística de 1 s lida por VIO), simulado (`TB RESULT: PASS`) e medido na placa B.
   Cinco bitstreams (md5 em `data/au15p_tap/build_frozen/MD5SUMS`): A, B (outra região do die),
   A′/B′ (as mesmas rotas + guarda de 250 ps por fase estática no clk_sys) e B″ (B + 125 ps).
   8 shmoos de VCCINT (0,949 → 0,725 V e volta, ~8 min cada), todos os dados em `data/au15p_tap/`.
3. **Análise e figuras por script** (`analysis/run_all.py` → `paper/generated/values.tex`).

## Resultados principais

- **16 nm (81 derivações independentes, implantações A–D, períodos de 10 a 18 ns; artigo
  atualizado em 23/11):** a leitura zero e o primeiro erro funcional ficam de −462 a +404 ps de slack
  um do outro (negativo: o erro vem antes); 32 das 81 falham ainda lendo positivo mesmo no extremo
  favorável do intervalo de 10 mV. A repetição de A três dias depois mudou m em +3 a +19 ps.
- **Modelo STA, 81 derivações:** 77 ps rms contra 175 ps da melhor constante (r = 0,93, inclinação
  0,81). Fora da amostra (as 70 novas): 77 contra 182 ps; C e D, com o Δ* commitado antes da medida
  (812b19e): 70 contra 199 ps. Sem A-S74, r = 0,93. Em toda implantação o STA vence a constante
  (Tabela II do artigo).
- **De que é feito o Δ\*:** chegada dos dois clocks (−476 a +512 ps, em degraus), roteamento até
  FF1 e FF2 (−342 a +166 ps) e um setup 394 ps menor que o STA dá ao FF2 em alguns locais de slice
  (23 derivações de B, C e D; a medida confirma: −9 ps de resíduo com o termo, +385 sem). Um ajuste
  de m às três partes dá pesos 0,85 (clock), 0,84 (setup) e 0,56 (roteamento): o STA exagera o
  roteamento. A mesma derivação em dois períodos: |m| maior na tensão de falha mais baixa em 11 de 14
  pares com |Δ\*| ≥ 100 ps (o STA de um corner não acompanha isso).
- **Guarda por implantação:** a de 254 ps deixaria 5 dos 113 casos atrasados (B e D); dimensionada
  pelo STA (pior Δ\* da implantação + 2 × 74 ps, o rms de 20/11) dá 348–594 ps e cobre os 113 casos
  com folga mínima de 132 ps.
- **Histórico, 20/11 (11 derivações, A e B a 10 ns):** −108 a +335 ps; 74 ps rms; repetível a 0,3
  passo; 7 das 11 atrasadas no extremo favorável.
- **Modelo STA** (sem a incerteza de 120 ps e o pessimismo de 153 ps em A e 207 ps em B cobrados a
  mais no caminho cruzado de FF1; antes o texto dava 154 ps para as duas): r = 0,84 (p = 0,001), Spearman 0,78, 74 ps rms contra 117 ps de um offset
  constante; B (medida depois de a correção ser achada em A) 62 ps rms; nenhuma tendência do
  resíduo com V_f. As estatísticas usam só A e B (as variantes com guarda são as mesmas rotas).
- **Robustez do STA só com os dados de 20/11 (superado pela bancada de 23/11):** a correlação
  dependia de A-S74 (sem ela, r = 0,68). A bancada mostrou que degraus de clock como o de A-S74 são
  comuns e que o STA os acompanha; a "diferença de clock constante por implantação" valia só para
  S70–S90.
- **Guarda:** 250 ps (A′, B′) baixam as leituras 14,24 ± 0,18 passos (254 ps) em 246 pontos
  pareados, V_f no mesmo degrau de 10 mV, as 11 derivações leem zero antes de falhar. 125 ps (B″,
  medida nesta revisão) baixam **8,06 passos (144 ps), não 7,0**, igual em todas as derivações: os
  degraus realizados diferem dos 125 ps nominais (0→4,5°: 144 ps; 4,5→9°: 110 ps), o que o offset
  estático de fase entre saídas do MMCM permite. Com B″ as
  5 derivações de B já leem zero primeiro. Dimensionada só pelo STA (pior Δ* + 2×rms) a guarda seria
  362 ps (3 ajustes).
- **28 nm (Run 1):** −4/−7/−14 passos a 1,1/1,0/0,9 V após 214,6 h; **um único deslocamento de
  14,3 ± 0,9 mV** da curva pós-burn-in reproduz os três corners (resíduo ≤ 0,7 passo; um offset
  constante deixa 5,5). Inversão térmica perto de 1,0 V.
- **16 nm, 37,4 h:** ≤ 0,5 passo nas duas placas (no artigo: placas 1 e 2, para não confundir com as
  implantações A/B; a placa 2 é a desta bancada). Run a 0,85 V, forno 85 °C, die da placa 1 a 113 °C.
- Verificador: acima de 2T de atraso (S142–S150 nas tensões mais baixas) o estímulo de período 2
  faz a captura atrasada de dois ciclos parecer correta; não afeta as derivações analisadas.

## Revisão de 23/11 (parecer aplicado)

Nota do parecer: 7/10 (aceite fraco); as mudanças de texto, figuras e análise estão listadas na
mensagem do commit. O que **falta na bancada** (placa 2 da AU15P; só SRAM, Vcore entre 0,70 e
0,92 V e de volta a 0,85 V no fim). **Roteiro passo a passo, com os comandos:**
[`bench/ROTEIRO_revisao.md`](bench/ROTEIRO_revisao.md). Com só a placa conectada (sem forno), o
roteiro cobre os itens 1 e 2; o item 2 vira a prioridade 1 (testado: `make_period.tcl` gera o
bitstream de 12 ns e o Δ* das 23 derivações não muda), e as derivações longas de A e B têm Δ*
previsto de −337 a +616 ps.

1. **Implantações C e D** da mesma RTL em outras regiões de clock (build de ~10 min e shmoo de
   ~8 min cada). São testes fora da amostra do modelo STA, hoje apoiado em A-S74; levam o n de 11
   para ~20–25 derivações independentes.
2. **Outro período de clock no mesmo checkpoint roteado** (só atributos do MMCM, como em
   `make_guard.tcl`). O Δ* não depende do período, e as derivações S94–S150, que já falham no topo
   da faixa, passam a cruzar a falha dentro dela.
3. Opcional: **derivações mais densas** entre S60 e S96 (passo de 2 estágios). Não recomendado
   agora: o item 2 já dá até 30 derivações novas sem mexer na RTL.
4. **Eixo de temperatura** (depende do PID do forno, item 3 abaixo): fora até o forno estar ligado.
5. **Placa 1** (a outra RV02A): fora enquanto só a placa 2 estiver conectada.

**Bancada de 23/11 feita (itens 1 e 2).**

- **O que foi medido:** 17 shmoos, com A e B a 12–18 ns e C e D a 10, 14 e 18 ns, sem nenhuma parada
  de segurança. Registro, builds e checksums em
  [`bench/REGISTRO_bancada_2026-11-23.md`](bench/REGISTRO_bancada_2026-11-23.md).
- **Resultado preliminar:**
  - São 81 derivações independentes. O Δ* dá r = 0,93 e 77 ps rms, sem parâmetro ajustado, contra
    175 ps da melhor constante.
  - C e D, com a previsão registrada antes da medida, dão 70 ps.
  - Sem A-S74 continua r = 0,93.
- **Feito em 23/11 (seção 5 do roteiro):** a análise separa a repetição de A (`shmooArep`, só
  repetibilidade) e inclui C, D e os períodos longos; o resumo e as Seções III, IV, V-A, V-B, V-C,
  VI e VII foram reescritos; a Fig. 3 tem as 81 derivações e a nova Tabela II resume o STA por
  conjunto. Os números de 20/11 continuam os mesmos.

## Pendências para o usuário (decisões suas)

1. **CFP do LATS 2027:** limite de páginas, revisão cega (há uma chave `\blindtrue` no `main.tex`),
   template e se o papel é A4 ou Letter.
2. **Relação com o D&T (não citado):** o LATS usa os corners da Run 1 e a validação de 16 nm; o D&T, a deriva in
   situ. Confirmar com o grupo que não há sobreposição indesejada.
3. **Forno:** se quiser o eixo de temperatura (desvio do sensor vs T), regravar o PID no Nano 33 IoT
   (`D&T 2027/10_DT_Monitor/firmware_forno`, na lixeira) — não fiz sem autorização.
4. **Placa 2 (a da bancada):** desde 23/11 está com o bitstream `impl_d18` (D a 18 ns) na SRAM e Vcore
   0,85 V. Ao desligar e religar, volta o design da flash, que nunca foi gravada.
5. Revisar o texto; sugestões de estilo são bem-vindas antes de 30/11.
6. **Depois da revisão de 23/11:** o repositório é privado e o artigo (modo não cego) aponta para
   ele; tornar público ou criar um repositório só com `hw/`, `bench/`, `data/` e `analysis/`.
   Conferir no DS931 v1.9 a linha MMCM_TSTATPHAOFFSET (citada na Seção V-C) e as versões dos
   datasheets (tiradas do bib do JICS).
   Se o resumo já foi enviado, atualizar com o de `paper/SUBMISSAO_titulo_resumo.txt` (199 palavras).
7. **Perguntar a quem rodou a Run 1:** a Nexys foi desligada ou reprogramada entre os corners de
   antes do burn-in (capturas de tela sem data) e o início do burn-in? O SBCCI 2026 diz que, ao
   religar, o sensor refaz a autocalibração e por isso só compara inclinações dentro de cada
   rodada; o resultado de 28 nm do LATS compara leituras absolutas de antes e depois. Argumentos a
   favor do LATS:
   - a "calibração" é a própria varredura, que parte sempre da mesma origem de fase;
   - um desvio por religar seria constante em passos, e uma constante deixa até 5,5 passos de
     resíduo nos três corners, contra 0,7 do deslocamento de 14,3 mV;
   - na AU15P, as leituras absolutas se repetiram com até 1 passo de diferença depois de reprogramar
     a placa três dias depois (outra família de FPGA).
   Se houve religamento, pôr uma frase com isso na Seção V-D. Durante o burn-in não houve: o log tem
   lacuna máxima de 6,2 s em 214,6 h, e as únicas 5 linhas inválidas estão no início.

**SBCCI 2026 conferido em 23/11** (`~/Documents/Trabalho/Artigos/SBCCI2026.pdf`):
- **Sem sobreposição de resultados.** O artigo compara forno bang-bang com PID (duas rodadas de
  23,08 h a 1,3 V e 80 °C) e não tem a Run 1, os corners, o deslocamento de 14,3 mV nem nada de
  16 nm. O LATS o cita só para o forno com PID, que a Run 1 usou (mesmos Kp, Ki e Kd no cabeçalho
  do log).
- **Passo do sensor.** Lá o passo é de 19,85 ps, aqui 17,857 ps.
  - O da Run 1 está confirmado: a versão em RTL de maio de 2026 usa ×10, VCO de 1 GHz (ver o
    HANDOFF; confirmado em simulação do MMCME2).
  - O do SBCCI 2026 é provavelmente o do projeto antigo da Nexys (`aging-study`, em diagrama de
    blocos), que usava ×9, VCO de 900 MHz e 19,84 ps. Mas o git só guarda esse projeto a partir de
    maio de 2026, e os logs das campanhas de 2025 e 2026 não registram o bitstream. Não dá para
    descartar que o SBCCI 2026 tenha usado por engano o valor da AU15P.
  - O artigo agora diz "VCO at 1 GHz", o que vale nos dois casos.
- **Terminologia.** "Never recalibrated" virou "without interruption", porque no SBCCI 2025/2026 cada
  varredura já se chama calibração.
- O `LASCAS2027.pdf` da mesma pasta é de outro assunto (controle térmico CEM43) e não se sobrepõe.
