# LATS 2027 — How Far from Failure Is a Zero Slack Reading?

Artigo, dados, hardware e contexto do trabalho submetido ao **IEEE LATS 2027** (Latin American Test
Symposium, 13–16/04/2027, Lima):

> **How Far from Failure Is a Zero Slack Reading? Predicting and Guard-Banding the Offset of an FPGA
> Aging Sensor**
> Arthur Pamplona, Danilo Alencar, Alisson Barros, Lucas Nogueira, Jarbas Silveira (UFC) e
> Fabian Vargas (IHP)

Prazos: título e resumo em 23/11/2026; artigo completo em 30/11/2026. Estado, decisões e pendências
estão em [`PLANO.md`](PLANO.md). O PDF atual é [`paper/main.pdf`](paper/main.pdf), com uma cópia
datada na raiz (`LATS2027_rascunho_*.pdf`).

## O trabalho em uma frase

O sensor de slack por varredura de fase (SBCCI 2025) foi posto lado a lado com um verificador de erro
funcional em 23 derivações de uma cadeia na AU15P (16 nm), e a tensão foi baixada até a falha. O
primeiro erro veio entre 108 ps antes e 335 ps depois da leitura zero. Esse desvio é o skew de
amostragem do próprio sensor: o STA o prevê por derivação (r = 0,84), e uma fase estática no clock
do sistema o transforma numa guarda de projeto. Na Nexys 4 (28 nm), um burn-in de 214,6 h equivale a
um deslocamento de 14,3 mV na tensão.

## Estrutura

| Pasta / arquivo | Conteúdo |
|---|---|
| `paper/` | Fonte do artigo: `main.tex` (IEEEtran conference), `refs.bib`, `figures/` e `generated/` (`values.tex` com todos os números do texto e `tab_taps.tex` com a Tabela I, gerados pelos scripts). Também `SUBMISSAO_titulo_resumo.txt` (título, autores, resumo e palavras-chave para o formulário). |
| `overleaf_LATS2027/` e `.zip` | Cópia do `paper/` pronta para subir no Overleaf (ver abaixo). É derivada: a fonte é `paper/`. |
| `analysis/` | `run_all.py` gera `values.tex`, a Tabela I e as figuras a partir de `data/`. `run1.py` e `fig_run1.py` (28 nm), `au15p_corners.py` (16 nm, 37 h), `tap_analysis.py`, `tap_offsets.py`, `tap_values.py` e `fig_tap.py` (16 nm, leitura zero vs. falha). `results.json` guarda os resultados intermediários. |
| `data/` | Dados brutos (nunca editados) e `SHA256SUMS`. Detalhes na seção seguinte. |
| `hw/au15p_tap/` | Projeto do experimento de derivações na xcau15p: `rtl/`, `constr/`, `sim/` (`run_sim.sh` imprime `TB RESULT: PASS`), `scripts/` (`build.sh`, `make_guard.tcl` para as variantes com guarda, relatórios de STA por derivação) e `build/` (saídas do Vivado, incluindo os checkpoints roteados usados pelas guardas). |
| `bench/` | Bancada: `tapbench.py` (grava a FPGA, lê as janelas, faz o shmoo de VCCINT), `stm32_link.py` (Vcore pelo ST-Link), `vivado_server.tcl` (JTAG/VIO/SYSMON) e `oven.py` (forno). |
| `contextoantigo/` | Contexto anterior: `HANDOFF_CLAUDE.md`, `Plano_Artigo_LATS2027.pdf` e a fonte do rascunho do JICS (`jics_source/`), que este artigo substitui. |
| `conversa_claude_LATS2027.txt` | A conversa de revisão que originou o plano deste artigo. |
| `IC-Aging-Environment-LATS-2027/` | Cópia do repositório do ambiente de envelhecimento do LESC/UFC (ramo do LATS 2027): aplicativos da bancada, firmware, hardware, publicações e teses do grupo. Só para consulta. |

## Dados e proveniência

| Pasta | O que é | Onde entra no artigo |
|---|---|---|
| `data/au15p_tap/` | 8 shmoos de VCCINT (0,949 → 0,725 V e volta, ~8 min cada) do experimento de derivações, medidos em 20/11/2026 na placa 2. Cada `tap_*.csv` tem um `.json` com o bitstream e os parâmetros. `shmoo1–3`: implantação A; `shmooB1–2`: B; `shmooAguard`, `shmooBguard`: A′ e B′ (+250 ps); `shmooBguard125`: B″ (+125 ps). | Seções V-A a V-C, Figs. 2–3, Tabela I |
| `data/au15p_tap/build_frozen/` | Os 5 bitstreams medidos (`impl`, `impl_b`, `impl_aguard`, `impl_bguard`, `impl_bguard125`), com `.ltx`, STA por derivação (`taps_sta*.csv`) e `MD5SUMS`. | Modelo STA (Seção V-B) |
| `data/nexys4_run1/` | Run 1 na Nexys 4 DDR (Artix-7, 28 nm): log do burn-in de 214,6 h a 1,4 V e 125 °C (`Tentative_1_*.csv`, do git `7f34155` do IC-Aging-Environment), varredura pós-burn-in (`Corners_20260602_*.csv`), capturas de tela dos corners pré, pós e a frio e sua transcrição (`corners_from_screenshots.csv`). | Seção V-D, Fig. 4 |
| `data/au15p/` | AU15P, placas A e B (no artigo, **placas 1 e 2**; a placa 2 é a da bancada): corners de 07 e 09/11, run de 37,4 h a 0,85 V com forno a 85 °C (`run_37h/`), relatórios dos bitstreams antigos e testes de temperatura. Recuperados da pasta `D&T 2027/10_DT_Monitor`. | Seção V-E, Tabela II |

## Reproduzir

```bash
# ambiente (uma vez)
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# números, tabela e figuras -> PDF
.venv/bin/python analysis/run_all.py
cd paper && pdflatex main && bibtex main && pdflatex main && pdflatex main && cd ..

# pasta e zip do Overleaf a partir de paper/
rm -rf overleaf_LATS2027/{main.tex,refs.bib,figures,generated} && mkdir -p overleaf_LATS2027/{figures,generated}
cp paper/main.tex paper/refs.bib overleaf_LATS2027/ && cp paper/generated/*.tex overleaf_LATS2027/generated/
cp paper/figures/fig_struct.tex paper/figures/*.pdf overleaf_LATS2027/figures/
rm -f overleaf_LATS2027.zip && (cd overleaf_LATS2027 && zip -qr ../overleaf_LATS2027.zip .)

# hardware (AU15P na bancada; Vivado 2025.2)
hw/au15p_tap/sim/run_sim.sh            # ~1 min, TB RESULT: PASS
hw/au15p_tap/scripts/build.sh          # ~10 min: build/impl/tap_top.bit e taps_sta.csv
vivado -mode batch -source hw/au15p_tap/scripts/make_guard.tcl \
  -tclargs <routed.dcp> <pasta_saida> <graus_clk_sys>   # variante com guarda, mesmas rotas
.venv/bin/python -I bench/tapbench.py program
.venv/bin/python -I bench/tapbench.py shmoo --from 0.92 --to 0.70 --back --windows 6 --tag shmoo
```

O LaTeX usado aqui é o TinyTeX (`~/.local/opt/tinytex`); no Overleaf, basta subir o zip e compilar
`main.tex` com pdfLaTeX.

## Regras do projeto

- Dados brutos nunca são editados; dados novos entram com `.json` de metadados e no `SHA256SUMS`.
- Todo número do artigo sai de `paper/generated/values.tex`. Para mudar um número, mude o script e
  rode `analysis/run_all.py` de novo, em vez de editar o `.tex` à mão.
- O artigo do D&T 2027 não é citado (decisão de 20/11/2026).
- Na bancada, só a SRAM da FPGA é gravada (nunca a flash), e o Vcore fica entre 0,70 e 0,92 V no PMIC,
  voltando a 0,85 V no fim.
