# Handoff — sessão de 06–07/10/2026 (artigo IEEE LATS 2027 + RTL multi-tap do Nexys4)

Documento para outra sessão do Claude retomar o trabalho sem reler a conversa. Escrito em 2026-11-19 a partir do estado do repositório nessa data, que é o mesmo do fim da sessão: nada foi commitado depois dela.

---

## 1. Quem é o usuário e as regras dele

- Pamplona (`arthupamplona@gmail.com`, git user "Pamplona"), bolsista na UFC, grupo de envelhecimento de FPGAs. Escreve em **português** e espera respostas em português.
- **Git:** nunca commitar nem dar push na `main`. Commits só na branch **`LATS-2027`** (local + `origin/LATS-2027`, criada a partir de `a40bb7a`). Push só com pedido explícito. A sessão está nessa branch, e **todo o trabalho abaixo está sem commit no working tree**.
- **Memória automática:** `~/.claude/projects/-home-Bolsistas-Documents-Pamplona-IC-Aging-Environment/memory/`, com `feedback_git_commits.md` e `project_lats_2027.md`.
- **Vivado:** **2026.1** em `~/2026.1/Vivado` (fora do PATH). Use `VIVADO_BIN=~/2026.1/Vivado/bin/vivado`; xvlog/xelab/xsim ficam no mesmo diretório. A licença foi instalada pelo usuário via `vlm` em `~/.Xilinx/Xilinx.lic`.
- **A máquina não tem** numpy, LaTeX, pandoc nem npm. Tem `python3` puro e `google-chrome`; PDFs foram gerados de HTML com `google-chrome --headless=new --print-to-pdf`.
- **Configuração do Claude Code:** o `/doctor` deixou o auto mode como padrão (`permissions.defaultMode: "auto"` em `~/.claude/settings.json`; backup em `settings.json.bak-doctor`).

---

## 2. O objetivo: artigo para o IEEE LATS 2027

- **Base:** o experimento do **JICS**. O artigo "An Auto-Tuning Aging Sensor for FPGA-Based Delay Degradation Monitoring…" (`publications/papers/gsem/JICS_Draft_Auto_Tuning_Aging_Sensor_Burn_In_2026.pdf`) **nunca foi publicado**, então o LATS o substitui.
- **Fora do escopo:** o usuário excluiu explicitamente o TCC do Danilo (bang-bang × PID, `publications/papers/gsem/Quantifying_the_Effect_of_Burn_In_Thermal_Control…pdf`).
- **Run 2 planejada pelo usuário:**
  1. contabilizar os mismatches;
  2. medir corners de tensão e temperatura antes e depois do burn-in;
  3. mostrar que slack ≈ 0 coincide com erro real;
  4. confirmar o envelhecimento mostrando que, depois, o sistema precisa de **tensão acima da Vmin antiga** e de **temperatura abaixo da Tmax antiga**.
- **Interpretação adotada,** que vale confirmar com o usuário: a fronteira de falha se desloca (Vmin↑, Tmax↓), medida por erro real e não só pelo sensor. O ponto nominal continua dentro da região segura, mas com menos margem.
- **Plano do artigo (discussão):** `publications/papers/lats2027/Plano_Artigo_LATS2027.pdf`, com fonte em `plano_lats2027.html`. Ele foi escrito **antes** do trabalho de RTL e tem partes **desatualizadas**:
  - usa 19,85 ps/passo; o certo é **17,857 ps**;
  - diz que o sweep do App_CornerSweep de 22/05 "foi até 0,70 V sem erro", o que é **falso**: o log `CornerSweep_Sweep_Init_20260522_214456.csv` (commit `99248ae`) não tem nenhuma linha de dados;
  - propõe a correção dos bloqueios B1–B4 e as decisões D1/D2, que **já foram implementadas** (seção 5).
- **Prazo e limite de páginas do LATS 2027:** não verificados. O plano supõe ~6 páginas no formato IEEE.

---

## 3. Dados já existentes (Run 1 = dados do JICS)

| Item | Valor / local |
|---|---|
| Log contínuo | `App_Nexys/test_logs/Tentative_1_20260524_203756.csv`, versão final no commit **`7f34155`** (retirado do tracking em `b908add`; extrair com `git show 7f34155:App_Nexys/test_logs/Tentative_1_20260524_203756.csv`) |
| Duração | 214,6 h (24/05 20:37 → 02/06 19:12), 1 Hz, 772 479 amostras válidas |
| Condição | VCCINT 1,400 ± 0,001 V (XADC, malha fechada); T_die 125,0 ± 1,8 °C; forno 93,9 ± 1,8 °C (PID) |
| Slack in-situ | 278,5 ± 3,1 **incrementos** (o JICS escreve "ps" por engano) |
| Correlações in-situ | slack × T: −1,47 inc/°C (R² 0,74); deriva temporal: −0,017 inc/h (R² 0,12), confundida com T |
| Formato do log | `time_sec,oven_temp_c,oven_setpoint_c,oven_output_pct,psu_voltage_v,psu_current_a,dut_temp_c,dut_slack,dut_volt` (pacote antigo, **sem mismatch**) |
| Corners pré-burn-in | só capturas de tela: `software/apps/App_Nexys/corners/high-temp_{high,normal,low}-volt.png` |
| Corners pós-burn-in | `*-end.png` + `data/sample_logs/Corners_20260602_191558.csv` (medianas 304/264/186) |

Leituras do bit 15 (caminho de 16 bits do JICS), em incrementos:

| VCCINT | Pré, ~104 °C | Pós, ~104 °C | Pós, ~46 °C |
|---|---|---|---|
| 1,10 V | 309 | 305 | 315 |
| 1,00 V | 271 | 263 | 264 |
| 0,90 V | 200 | 186 | 168 |

- **Envelhecimento:** Δ de −4 / −8 / −14 inc (−79 / −159 / −278 ps), maior em tensão baixa. Equivale a ~13–18 mV de Vmin consumida.
- **Inversão térmica (ZTC ≈ 1,0 V):** a 1,1 V o calor deixa o caminho mais lento, a 1,0 V não muda nada e a 0,9 V o **frio** é que deixa mais lento. "Tmax" só faz sentido para caminhos que falham acima de ~1,0 V.
- Run 1 e Run 2 usam a mesma placa e o mesmo flow; a placa da Run 1 já tem 215 h de stress. Recomendação: placa nova para a Run 2, de preferência duas, com o setup do App_2Nexys.

---

## 4. Achados técnicos que corrigem o JICS e a RTL antiga

1. **Passo de fase = 1/56 do período do VCO.** O `clk_wiz_0` do Nexys4 usa ×10 sobre 100 MHz, VCO de 1 GHz, então **17,857 ps**. O valor de 19,85 ps é da UltraScale+ (SBCCI, ×9, VCO de 900 MHz). Confirmado no modelo MMCME2_ADV do xsim, que acumula o deslocamento além de 56 passos.
2. **A Tabela I do JICS é cópia da Tabela I do SBCCI,** que media uma cadeia de 50 inversores, não o RCA. Não pode ser reaproveitada.
3. **Janela de observação:** FF3 amostra 99° (2,75 ns) depois do `clk_sys`, então avanços de fase acima de ~7,25 ns (~406 passos) não aparecem. `MAX_STEPS` = 390.
4. **O sensor mede o slack módulo T (10 ns).** O sinal alterna a cada ciclo; um caminho que estoura mais de ~3 ns mostra uma leitura positiva falsa. Exemplo verificado: atraso de 14,04 ns lê 334 = (2T − t)/passo.
5. **O verificador de captura tem aliasing módulo 2T.** Um caminho com atraso entre 2T e 3T captura o valor "certo" e não acusa erro (verificado no netlist roteado, bit 39 no canto lento). Numa varredura de tensão, uma derivação longa que para de errar ao baixar V está nesse regime; não se recuperou.
6. **Bugs da RTL antiga do JICS, já corrigidos:**
   - B1: `failure_holder` comparava saídas de somadores diferentes, por isso "FALHA: SIM" o tempo todo;
   - B2: `error_count` de 16 bits dava wrap em ~0,65 ms;
   - B3: `wrong`/`correct` eram somas gravadas no alarme, não contadores;
   - B4: o caminho de 16 bits só falharia por volta de ~0,78 V, no limite da retenção de configuração (VDRINT 0,75 V);
   - o controlador antigo tinha atraso de 1 passo na leitura;
   - os botões entravam sem sincronização.
7. **A RTL de Run 1 = HEAD antes desta sessão.** O commit `9d72faa` (22/05) tem `.sv`, constraints e scripts idênticos; só o IP do clock foi regenerado em `d4b3416`, com o `.xci` igual. Build de referência no 2026.1: WNS +0,184 ns; caminho do bit 15 com 9,302 ns no canto lento e 3,924 ns no rápido (FF2).
8. **A branch `origin/experimental-multi-sensor` não serve.** O "somador" dela é `a + b` comportamental (CARRY4), e o sensor amostra uma flag que fica sempre em 0.

---

## 5. O que foi implementado (sem commit)

Tudo em `hardware/fpga/xilinx/nexys4_ddr/`. A documentação canônica está no `CLAUDE.md` desse diretório e no `PROTOCOL.md` da raiz.

**Arquitetura (`src/rtl/`)**
- **`aging_sensor/cut_tapped_chain.sv` (`u_cut`):** cadeia LUT ripple de 40 estágios com operandos `{..0101, toggle, ~toggle}` + `..1010`, em que todo estágio alterna a cada ciclo. São **7 derivações** nos bits **15, 19, 23, 27, 31, 35 e 39**; o bit 15 é o caminho do JICS. Cada derivação tem um `modern_sensible` (FF1 em psclk, FF2 em clk_sys, XOR1, FF3 em clk_en) e um verificador `err_q = FF2 ^ toggle_ref`, onde `toggle_ref` é uma réplica que mantém a carga do JICS no fio de lançamento.
- **`aging_sensor/canary_chain.sv` (`u_canary`):** canário de 28 bits, `a = {..0101, cnt[15:0]}`, com o carry completo de 27 estágios 2× a cada 65 536 ciclos. Captura registrada `cap_q` comparada com uma referência CARRY4 registrada. Tem o mesmo número de estágios da derivação do bit 27.
- **`aging_sensor/sweep_controller.sv` (`u_sweep`):** uma varredura de fase para todas as derivações. Depois de cada PSDONE espera FLUSH=6 ciclos e observa por OBSERVE=8; o resultado é o primeiro passo com alarme, ou 0xFFFF se não houver até 390. Depois volta a fase a 0. São ~6 000 varreduras/s.
- **`aging_sensor/window_stats.sv` (`u_stats`):** por janela entre dois `'T'`, para cada derivação: última leitura, mínimo, máximo, contagem, soma (a média sai abaixo de 1 passo) e ciclos com captura errada; também os erros do canário. Flags persistentes são zeradas por `'R'`.
- **`uart/packet_tx.sv`:** pacote de **181 bytes** = 15 legados + extensão (`0xA5`, versão 2) + CRC16-Modbus. Ignora `'T'` durante a transmissão (~190 ms).
- **`top/nexys4_aging_top.sv`:**
  - parâmetros `BAUDRATE` (9600) e `MAX_STEPS` (390);
  - reset síncrono no `clk_sys` e `count_en` só 1024 ciclos após o reset;
  - LEDs LD0 (alarme bruto do bit 15), LD1 (canário persistente), LD2 (bit 27 persistente) e LD3–LD9 (derivação errou nos últimos ~170 ms);
  - VIO com as mesmas larguras de probe;
  - **`KEEP_HIERARCHY`** em `u_cut`, `u_canary` e `u_sweep`.
- **`temp_catcher.sv`:** agora exporta também os códigos brutos de 12 bits do XADC.
- **`uart_rx`/`uart_tx`:** taxa parametrizada. O bit dura COUNT+1 ciclos, o que é desprezível a 9600 baud.
- **Removidos:** `adder_canary.sv`, `controller_controller.sv`, `failure_holder.sv`, `sensor_stream.sv` e o `sim/sim.v` antigo.

**Pacote.** O mapa de bytes completo está no `PROTOCOL.md`.
- **Bytes 0–14:** mesmo layout de antes.
  - 3–4: última leitura do bit 15;
  - 8: canário errou na janela;
  - 9–12: bits [27:12] da última soma errada do canário e do valor esperado;
  - 13–14: total de erros do canário, saturando em 65535.
- **Compatibilidade:** os apps atuais leem só esses 15 bytes e limpam o buffer antes de cada `'T'`, então continuam funcionando.
- **Extensão:**
  - cabeçalho até o byte 52: ciclos e varreduras da janela, códigos do XADC, flags, máscaras de erro e de persistência, `max_steps`, erros do canário (janela e total) e última soma errada/esperada;
  - um registro de 18 bytes por derivação a partir do byte 53;
  - CRC nos bytes 179–180.
- **Decodificador Python:** `software/core/ic_aging_core/protocols/nexys_packet.py:decode_extended_packet`, testado com os pacotes da simulação (CRC confere, bit invertido é rejeitado, 15 bytes legados idênticos).

**Constraints**
- **`src/constraints/cut_region_timing.xdc`** (novo, editado à mão, só implementação):
  - região exclusiva `pblock_cut` = `SLICE_X0Y70:SLICE_X5Y99`, com `EXCLUDE_PLACEMENT`;
  - **alvos por derivação** `set_max_delay -datapath_only` de 1,6 ns + 0,55 ns × (k−1): 9,3 / 11,5 / … / 22,5 ns, e 15,9 ns no canário.
  - Por que os alvos: com um limite frouxo (40 ns), o roteador liga o carry nas entradas lentas das LUTs, a 0,32 ns por LUT contra 0,12 ns, e a cadeia sai ~45% mais lenta.
- **`src/constraints/fixed_pnr_constraints.xdc`:** **gerado** (forma travada). LOC/BEL de 310 células, LOCK_PINS de 173 LUTs e FIXED_ROUTE de 96 redes do caminho medido. Fonte: `references/fixed_pnr_multitap.dcp` (3 MB, fora do git).
  - Ficam de fora os CARRY4, que o Vivado posiciona como macro, e as redes do comparador do canário depois do `cap_q`. Travá-los causava erro de DRC `RTSTAT-5` (antenas parciais por route-through de LUT).
  - Se a RTL de `u_cut`/`u_canary` mudar: esvazie o arquivo (mantendo o cabeçalho) e rode `--refresh-ref`.
- **`references/fixed_pnr.dcp`:** é o checkpoint do design antigo, mantido só como histórico.
- **`Nexys-4-DDR-Master.xdc`:** pinos dos `tap_led[0..6]`: N14, R18, V17, U17, U16, V16 e T15.

**Scripts (`scripts/`)**
- **`build_bitstream.sh [--refresh-ref]`:** gera o bitstream, os relatórios e, ao final:
  - `artifacts/cut_paths.{txt,csv}`, via `report_cut_paths.tcl`: slack de cada derivação contra 10 ns nos cantos lento e rápido, leitura prevista e s_fail previsto;
  - `artifacts/timesim/`: netlist com SDF dos cantos lento e rápido.
- **`extract_fixed_pnr_constraints.{sh,tcl}`:** regenera as travas.
- **`run_behavioral_sim.sh`:** testbench `src/sim/tb_nexys4_aging_top.sv` com MMCM/XADC reais, `lut_full_adder_delay.sv`, atraso por estágio controlado por `sim_delay_pkg::stage_ns` e UART a 4 Mbaud. Deve imprimir `TB RESULT: PASS`.
- **`run_timing_sim.sh`:** netlist roteado nos cantos lento e rápido, com `tb_timesim.sv`, `uniquify_timesim.py` e `compare_timesim.py`. Deve imprimir `TIMESIM RESULT: PASS`. Leva ~30 min.
- **`check_layout.sh` e `create_project.tcl`:** atualizados para os arquivos novos.

**Documentação atualizada:** `PROTOCOL.md`, o `CLAUDE.md` raiz, o `CLAUDE.md` do nexys4_ddr, `docs/SOURCE_MANIFEST.md`, `references/README.md` e um aviso de "superado" no `IMPLEMENTATION_ROADMAP.md`.

**Feito pelo `/doctor` antes do trabalho de RTL, também sem commit:**
- o `CLAUDE.md` raiz foi enxugado, e as partes específicas de cada app foram para `software/apps/*/CLAUDE.md` e `firmware/thermal_chamber/PID_Controller/CLAUDE.md`;
- foram corrigidos fatos desatualizados (o caminho do bitstream e o protocolo `'F'`).

---

## 6. Verificação feita, toda aprovada

1. **Simulação comportamental:** 11 pontos de atraso por estágio, mais o teste do `'R'`, todos aprovados.
   - Leituras iguais ao ideal, com diferença máxima de 1 passo.
   - Erros em 100% dos ciclos exatamente quando k·d > 10 ns, e 0 fora disso.
   - Aliasing previsto confirmado.
   - Bit 27: a leitura cai 16 → 7 → 3 com slack de 0,280 / 0,118 / 0,037 ns; os erros e o canário começam em −0,017 ns.
2. **Build final:** sem erros nem avisos críticos, WNS +0,146 ns. Utilização: ~3,2k LUT, ~4,6k FF, 2 DSP.
   - **Reprodutibilidade:** com as travas, o `cut_paths.csv` das 7 derivações ficou idêntico ao do build de referência; o canário variou 12 ps (o fio de lançamento do contador não é travável).
   - **Auditoria:** DRC só com avisos, a maioria do `dbg_hub`. Metodologia com 312× `TIMING-11` (intencional, `-datapath_only`) e 32× `TIMING-18` (E/S). CDC só do debug core.
3. **Análise estática por derivação (build final):**

| Bit | 15 | 19 | 23 | 27 | 31 | 35 | 39 | canário |
|---|---|---|---|---|---|---|---|---|
| Datapath FF1, canto lento (ns) | 8,912 | 11,055 | 12,939 | 14,829 | 17,064 | 19,230 | 21,267 | 14,574 |
| Datapath FF1, canto rápido (ns) | 3,812 | 4,747 | 5,612 | 6,427 | 7,378 | 8,308 | 9,180 | 6,334 |
| s_fail previsto, canto lento (passos) | −1,6 | −15,6 | −2,1 | +0,1 | −9,9 | −30 | −39 | — |

4. **Previsão no silício a ~104 °C,** calibrada com a Run 1 (α = silício / canto lento do JICS: 1,1 V 0,490; 1,0 V 0,564; 0,9 V 0,702; 1,4 V/125 °C 0,540; modelo α = A·V/(V−0,55)^1,3):

| Bit | 15 | 19 | 23 | 27 | 31 | 35 | 39 | canário |
|---|---|---|---|---|---|---|---|---|
| V de falha estimada | 0,77 | 0,82 | 0,87 | 0,92 | 0,98 | 1,05 | 1,11 | 0,91 |
| Burn-in 1,4 V/125 °C | ok | ok | ok | ok | ok (0,78 ns) | falha | falha | ok |

   Extrapolações abaixo de 0,9 V são as mais incertas. Os bits 35 e 39 são os candidatos para o eixo de temperatura, porque falham acima do ZTC.
5. **Simulação de timing do netlist roteado:** os dois cantos aprovados.
   - **Canto lento:** a simulação fica +22 passos (393 ps) acima da análise estática, com espalhamento de 1 passo. O bit 15 passa (lê 62). Os bits 19–35 erram em 100% dos ciclos, com as leituras de aliasing 291 / 160 / 42. O bit 39 não acusa erro (aliasing 2T). O canário teve 11 erros.
   - **Canto rápido:** +28 passos (500 ps), espalhamento 0. As 7 derivações passam, lendo 347 / 292 / 246 / 200 / 145 / 93 / 45. Canário sem erro.
   - **Por que existe o deslocamento:** a análise estática desconta setup, incerteza e derating de clock. O critério que importa é o deslocamento ser **constante entre derivações**.
   - **Defeito do xsim 2026.1:** ele aplica o atraso de fio (`INTERCONNECT`) do SDF por **nome de folha + pino** quando o nome se repete em vários módulos: todo `CARRY_LUT`, todo `FF1` recebe a primeira entrada do SDF. A cadeia simulava ~2× mais lenta. Correção: `uniquify_timesim.py` renomeia as 7 475 folhas no netlist e no SDF, incluindo as linhas `initial assign <inst>.notifier`.
   - **Outras opções da simulação:** use `-pulse_e 0 -pulse_int_e 0`, senão glitches viram X e travam a máquina de estados do `temp_catcher` (o XADC acusa "DEN before DRDY"). `--notimingchecks` derruba o xelab.

---

## 7. Pendências e próximos passos

1. **Integrar o pacote estendido aos apps** (App_Nexys, App_CornerSweep e talvez App_2Nexys). Os apps precisam ler os 181 bytes, validar o CRC com `decode_extended_packet` e gravar no CSV, por derivação, média, mínimo, máximo, erros e taxa, além do canário e dos códigos do XADC. Também enviar `'R'` no início de cada etapa. **Sem isso, a Run 2 não registra os mismatches.** Ainda não foi feito; o usuário não respondeu se quer.
2. **Estender o App_CornerSweep para o shmoo V×T:** passo fino de 2–5 mV perto da falha, alguns passos além do primeiro erro, lista de temperaturas e critério estatístico de Vmin.
3. **Atualizar o PDF do plano do LATS** com o que está na seção 4 e com a arquitetura nova.
4. **Teste em placa.** Nada foi gravado em hardware ainda. Conferir na bancada: leituras do bit 15 perto da Run 1, contadores de erro em 0 no nominal, e falha aparecendo nas derivações longas ao baixar V.
5. **Commit na `LATS-2027`** quando o usuário pedir. O `references/fixed_pnr_multitap.dcp` é binário de 3 MB, a política de dados do repo permite checkpoints em `references/`.
6. **Opcional:**
   - definir `CFGBVS VCCO` / `CONFIG_VOLTAGE 3.3` no XDC (aviso de DRC);
   - reduzir o |s_fail| das derivações 35 e 39 casando os caminhos de FF1 e FF2;
   - confirmar com o usuário a interpretação de "tensão maior que a mínima / temperatura menor que a máxima" diante do ZTC ≈ 1,0 V.

---

## 8. Como rodar

```bash
cd hardware/fpga/xilinx/nexys4_ddr
export VIVADO_BIN=~/2026.1/Vivado/bin/vivado
scripts/check_layout.sh
scripts/build_bitstream.sh --jobs 8          # ~6 min; artifacts/aging_study_nexys4ddr.bit + cut_paths + timesim/
scripts/run_behavioral_sim.sh                # ~90 s; "TB RESULT: PASS"
scripts/run_timing_sim.sh                    # ~30 min; "TIMESIM RESULT: PASS" nos dois cantos
# re-travar o CUT após mudar u_cut/u_canary: esvaziar fixed_pnr_constraints.xdc (manter cabeçalho) e
scripts/build_bitstream.sh --jobs 8 --refresh-ref   # depois um build normal para confirmar cut_paths idêntico
```

---

## 9. Armadilhas encontradas (não repetir)

- **Nomes de células:**
  - `u_cut/g_tap[N].u_sense/FF1`: o generate e a instância são unidos por **ponto**, não por `/`;
  - `u_cut/u_chain/FA[k].fa/{SUM_LUT,CARRY_LUT}`;
  - contadores do canário: filtrar `IS_SEQUENTIAL && NAME =~ u_canary/cnt_reg*`, porque o padrão também pega CARRY4.
- **`flatten_hierarchy=rebuilt`** move lógica para dentro de submódulos. Sem `KEEP_HIERARCHY`, os contadores dos LEDs entravam na região do CUT.
- **Erro de build cancela os relatórios.** Um build que falha no `write_bitstream` não regenera `cut_paths.csv`. Apague `artifacts/` antes de comparar, senão você compara com o arquivo velho.
- **Unidades de `$time`:** em testbench com `timescale 1ns/1ps`, `$time` é em ns, mas `%t` imprime em ps.
- **xvlog/xsim:** vários `always_ff` escrevendo bits diferentes da mesma variável violam a regra de driver único. Use variáveis por bloco generate mais `assign` em saídas `wire`.
- **Correção de um erro da sessão anterior (Haiku):**
  - o resumo do SBCCI tinha números errados; na Tabela I, o Corner4 vale 704, não 2410;
  - o bloco `"autoMode": {"enabled": true}` que foi sugerido não existe. A chave certa é `permissions.defaultMode`.
