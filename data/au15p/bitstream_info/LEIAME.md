# Bitstreams da AU15P (xcau15p-ffvb676-1-i)

Os dois foram compilados em 29/10/2026 com o **Vivado 2025.2** (`/home/andre/2025.2`), a
partir do projeto `hardware/fpga/xilinx/ultrascale_plus` do `origin/main` (commit `a40bb7a`,
no worktree `IC-Aging-Environment-au15p`). Nos dois, o `clk_wiz_0` foi recriado no 2025.2
com os mesmos parâmetros (Rev. 17 no lugar da Rev. 18 do 2025.2.1; os 256 parâmetros da IP
e os 316 do modelo são iguais). Cada `.bit` tem o `.ltx` de mesmo nome com os probes do VIO,
que o D&T Monitor usa para ler o slack pela JTAG.

| Arquivo | O que é | Placa A (DNA …2D020185) | Placa B (DNA …2D020285) |
|---|---|---|---|
| `au15p_sbcci_origin-main.bit` | o design do `origin/main` como está | **não mede slack**: o controlador varre sem parar (estados 1–2) e nunca termina | não testado |
| `au15p_TESTE_caminho_critico.bit` | o mesmo design com o somador de 256 bits trocado por `au15p_TESTE_caminho_critico_somador.sv` | **mede**: 409–410 contagens (≈ 8.12 ns), estável em ±1, MMCM com lock | **mede**: 408–409 contagens, ±1, MMCM com lock (die a ~98 °C) |

A placa B sobe sozinha um design da flash, que não é nenhum destes dois (tem um VIO que não
bate com os `.ltx` daqui). O app grava o de teste por cima, só na SRAM.

md5 do `.bit`: origin-main `3ffc1161ea805097eeb7fe12c98c8962`, TESTE `d29ab94886749d86255f392ac4efb474`.

## Por que o do origin/main não mede

No `fpga_unified_top.sv`, a entrada do sensor (`crit_end`) é o `error_flag` do
`ripple_carry_adder`, que compara `combined_sum` com `op_a + op_b`: a mesma conta dos dois
lados. Com o timing atendido, ele fica sempre em 0. O sensor (`modern_sensible`) precisa ver
o caminho crítico **mudar** a cada ciclo; sem transição, o alarme nunca dispara, a varredura
não termina, o SYSMON do design nunca é lido e nenhum pacote sai pela UART.

## O que o de teste muda

Só o arquivo do somador (o resto do RTL, a XDC e as IPs são os mesmos). `op_a` alterna entre
`0x55…55` e `0x55…56` e `op_b = 0xAA…AA`: a soma alterna entre `0xFF…FF` e `0x00…00`, e a
borda 1→0 do bit 255 só acontece depois que o carry atravessa os 256 bits. Esse bit vira o
`error_flag` (= `crit_end`). É a mesma ideia do sensor do Nexys (`adder_canary.sv`).
Timing atendido (WNS +0.353 ns), 75 CARRY8, 1.8 % dos LUTs.

**Não está no git.** Se o grupo adotar essa correção, ela entra no RTL do branch
`au15p-telemetria` (e o RTL v2 parte dela).

Os relatórios de timing e utilização de cada um estão ao lado (`*_timing.rpt`, `*_utilization.rpt`).

## `au15p_hub_B.bit` — arquitetura B (04/11/2026; build atual de 05/11)

Compilado com o **Vivado 2025.2** a partir do worktree `IC-Aging-Environment-au15p` (branch
`au15p-telemetria`, sem commit), top `fpga_hub_top`, com `scripts/build_hub.sh`. O
`clk_wiz_0` foi recriado no 2025.2 com os mesmos parâmetros. Fontes novas em
`hardware/fpga/xilinx/ultrascale_plus/src/rtl/hub/`; simulação em `sim/hub/run_sim.sh`.

| | |
|---|---|
| md5 | `d6a64886e871487da64ddf394605231e` |
| USR_ACCESS | `0x2DB4C51F` = 2026-11-05 12:20:31 (data da compilação; o app usa para reconhecer o design) |
| Timing | WNS +0.459 ns, WHS +0.033 ns (no hub de depuração da Xilinx), WPWS +2.000 ns (relatório ao lado). O pior caminho é o FF1 → FF3 do próprio sensor (captura a 50°), como no TESTE (+0.353 ns). Sem fixar as células do sensor, a folga desse caminho variava de +0.09 a +0.40 ns entre builds; a XDC agora põe FF1, XOR1 e FF3 no `SLICE_X44Y140` e FF2 no `SLICE_X44Y139` |
| Uso | 2.96 % dos LUTs, 2.11 % dos registradores, 1 DSP |
| Somador | o mesmo RCA corrigido do TESTE (`src/rtl/hub/ripple_carry_adder_toggle.sv` = `au15p_TESTE_caminho_critico_somador.sv`) |
| VIO e `.ltx` | os mesmos probes do TESTE (`phase_count`, `ctrl_state`, `locked`, `sensor_alarm`, …): a leitura de reserva pela JTAG continua valendo |

O que ele faz de diferente do TESTE:
- Manda um quadro `FPGA_SENSOR` por segundo e o `FPGA_INFO` (DNA, USR_ACCESS) no formato do
  `PROTOCOL_V2.md`, a 125 000 baud, para o STM32 (W12) e para o TX do J9 (Y26).
- **Varredura contínua:** cerca de 8000 varreduras por segundo, com contagem, mínimo, máximo,
  soma e soma dos quadrados por janela. O `slack_last` equivale à varredura única por
  segundo do TESTE e do SBCCI.
- Temperatura e VCCINT: média de 1024 leituras do SYSMON por janela.
- **Sem bypass:** o RX do J9 não chega mais ao STM32.
- **Trava:** a linha para o STM32 só sai do repouso depois do `STM_HELLO` do firmware B.
- Toda varredura começa na mesma fase: um passo interrompido é devolvido.
- O `FPGA_INFO` também sai sempre que a linha para o STM32 é liberada: o STM32 recebe a identificação
  logo depois de o FPGA ser gravado ou de o STM32 reiniciar.

**Atenção para a análise:** é outra implementação física do RCA (outro place & route), então
a contagem de slack de base **não precisa dar 409** como no TESTE. Compare a deriva de cada
placa com ela mesma, sempre com este bitstream.

**Build de 05/11:** o `USR_ACCESS` do `FPGA_INFO` passou a ser lido direto do `DATA` do
`USR_ACCESSE2`. No build de 04/11 (`0x25B56CF5`, md5 `8b4eab03…`), ele esperava o `DATAVALID`,
que na placa não fica em 1, e o `FPGA_INFO` saía com o campo zerado (a JTAG lia certo). O
resto do RTL não mudou.

Conferido em 05/11 com o `verificar_hub.py` e o firmware B versão 2, sem forno: 58 janelas
seguidas, nenhuma faltando, nenhum erro de enlace durante a medição.

| | build de 04/11 (`0x25B56CF5`) | **build de 05/11 (`0x2DB4C51F`, o atual)** |
|---|---|---|
| placa A | slack 403 (σ 0), ~9100 varreduras/janela, die 61 °C | slack 410,9 (409–412, σ 1,1), ~8930 varreduras, die 61 °C |
| placa B | slack 392 (390–403, σ 3,3), ~9350 varreduras, die 105 °C | slack 409,0 (408–410, σ 1,0), ~8970 varreduras, die 105 °C |

**A contagem de base muda de um build para outro**, mesmo com as células do sensor fixas,
porque o roteamento do somador muda. Para a run, **congele este bitstream** (md5 acima) e não
recompile entre a referência e o fim da run.

Nas duas, o DNA do `FPGA_INFO` (DNA_PORTE2) veio na **mesma ordem de bits** que o `FUSE_DNA`
da JTAG. Grave sempre depois do firmware B (`../PROTOCOLO_RUN.md`). Gravar ou reiniciar o
STM32 apaga a configuração do FPGA.

## `au15p_multi_B.bit` — várias cadeias, posição fixa (10/11/2026), congelado

Variante da arquitetura B com **9 cadeias** e um sensor por cadeia, para o burn-in da D&T
2027. Uma cadeia só não basta na AU15P, que envelhece devagar: na run de 07–09/11, a deriva
ficou abaixo de um passo do sensor. Compilado com o **Vivado 2025.2** no worktree
`IC-Aging-Environment-au15p` (branch `au15p-telemetria`, sem commit), top `fpga_multi_top`,
com `scripts/build_multi.sh`. Fontes, desenho e método em
`hardware/fpga/xilinx/ultrascale_plus/src/rtl/multi/LEIAME.md`.

| | |
|---|---|
| md5 | `b4f0b00946a7100a04c1ac03d4fe3cd3` (`.ltx` igual ao do `au15p_hub_B`; checkpoint `a844810ab1390bf1c6e29fb04b6946ad`) |
| USR_ACCESS | `0x55B4F7E0` = 2026-11-10 15:31:32 |
| Timing | WNS +0.450 ns, WHS +0.007 ns (no hub de depuração da Xilinx) |
| Uso | 8.45 % dos LUTs, 7.01 % dos registradores, 542 CARRY8 (5.6 %) |
| VCCINT (estimativa do Vivado a 0.85 V, cadeias alternando a cada ciclo) | 0.115 A a 25 °C e 1.111 A a Tj 115 °C (o `au15p_hub_B` dá 1.077 A); a fuga estática domina |
| Posição | cadeias, sensores, clocks e 4 registradores do VIO fixos pela `src/constraints/fpga_multi_fixed_pnr.xdc` do worktree |
| Placa | gravado na placa A em 10/11/2026 18:25 (só SRAM); quadros conferidos, ver "Primeira leitura" |

O que ele manda: os mesmos `FPGA_SENSOR` e `FPGA_INFO` do `au15p_hub_B` (o `FPGA_SENSOR` é a
cadeia 0), mais um quadro **`FPGA_CHAIN` (0x03, 30 bytes)** por cadeia a cada janela, 100 ms
depois do fim da janela e a cada 50 ms. Mesma linha, mesmo baud e mesma trava do `STM_HELLO`.
O firmware B do STM32 repassa os quadros sem ser regravado.

| Cadeia | Tipo | Tamanho | Atraso (ns) | Passos previstos |
|---|---|---|---|---|
| 0 | soma inferida, igual à das placas | 256 bits | 3.570 | 295 |
| 1 | CARRY8 instanciada | 128 bits | 1.956 | 397 |
| 2 | CARRY8 instanciada | 256 bits | 2.808 | 353 |
| 3 | CARRY8 instanciada | 512 bits | 4.391 | 277 |
| 4 | CARRY8 instanciada | 1024 bits | 7.486 | 119 |
| 5 | LUT | 8 estágios | 2.764 | 331 |
| 6 | LUT | 16 estágios | 3.831 | 279 |
| 7 | LUT | 24 estágios | 4.759 | 238 |
| 8 | LUT | 32 estágios | 6.551 | 150 |

O atraso é o do caminho que alterna (de `op_a[0..1]` ao FF2 do sensor), no corner lento do
Vivado. Os passos previstos são a folga no FF1 com a fase na origem dividida por 19.841 ps.
A escala da placa é outra (a placa A lê ~408 onde o Vivado prevê 319 para o `au15p_hub_B`),
então compare a deriva de cada cadeia com ela mesma. A tabela completa está em
`au15p_multi_B_cadeias.txt`.

**Primeira leitura (placa A, 10/11/2026 18:26, 75 janelas, forno desligado, app fechado).**
Gravado pela JTAG só na SRAM (DNA …2D020185, USR_ACCESS `0x55b4f7e0`, DONE 1). Lido no
ST-Link da A, com o firmware B v6 (HSE) sem regravar: 75 `FPGA_SENSOR`, 2 `FPGA_INFO`
(`rtl_version` 3) e as 9 `FPGA_CHAIN` em todas as 75 janelas, 0 janelas faltando, 0 `$FPG`
inválidos. A cadeia 0 bateu com o `FPGA_SENSOR` nas 75. VCCINT sem a malha do app: 0.875 V no
SYSMON (Vc 0.846 V); die 52 °C; ~8180 varreduras por janela.

| Cadeia | Tipo | Tamanho | Média (passos) | σ na janela | Faixa | Previsto |
|---|---|---|---|---|---|---|
| 0 | soma inferida | 256 | 395.03 | 0.65 | 394–400 | 295 |
| 1 | CARRY8 | 128 | 449.03 | 0.16 | 449–450 | 397 |
| 2 | CARRY8 | 256 | 442.53 | 0.74 | 438–443 | 353 |
| 3 | CARRY8 | 512 | 388.00 | 0.19 | 387–389 | 277 |
| 4 | CARRY8 | 1024 | 293.67 | 0.66 | 293–298 | 119 |
| 5 | LUT | 8 | 417.66 | 0.47 | 417–418 | 331 |
| 6 | LUT | 16 | 387.99 | 0.17 | 387–389 | 279 |
| 7 | LUT | 24 | 358.05 | 0.28 | 356–359 | 238 |
| 8 | LUT | 32 | 298.16 | 0.40 | 296–299 | 150 |

A ordem é a prevista. Medido ≈ 214.9 + 0.613 × previsto, com resíduos de até ±11 passos (a
cadeia 2 fica 11 acima, a 1 e a 8 ficam 9 abaixo): a 52 °C e 0.875 V o silício é ~0.6× o
corner lento. Pela diferença entre as cadeias 1 e 4, cada CARRY8 vale ~27.5 ps; pela das
cadeias 5 e 8, cada estágio de LUT vale ~99 ps. Da 1 para a 2 o ganho é só ~8 ps por CARRY8,
fora da tendência: a parte fixa (ida até o sensor, clock do FF1) dessas duas deve ser
diferente. Estes valores são de uma tensão sem malha; a base da run é a de 0.85 V.

**O app grava o bitstream escolhido em "Bitstream do modo hub"** (`hub_bitstream` no
`settings.json`; desde 10/11/2026 19 h, o `au15p_multi_B`). Com "Programar" marcado, um FPGA
com o outro bitstream conta como design errado e é regravado. Religar a placa ou reiniciar o
STM32 apaga o FPGA.

**Posição fixa conferida:** com a XDC, dois builds deram as mesmas 7387 posições e as mesmas
5172 rotas das cadeias e dos sensores, fio a fio. Um dos builds tinha outra estratégia de
implementação (Performance_Explore) e outra janela (500 ms). O caminho de dados de cada
cadeia saiu igual nos dois. Da árvore de clock, só ficam fixos a raiz, o MMCM e os buffers:
a folga prevista do FF1 variou até 0.022 ns (≈ 1 passo) entre os builds, em algumas cadeias.
Mesmo assim, **use sempre este `.bit`** (md5 acima) do começo ao fim de uma run.

**No D&T Monitor (desde 10/11/2026):** escolha `au15p_multi_B.bit` em "Bitstream do modo hub"
na configuração. O app decodifica o `FPGA_CHAIN`, mostra uma tabela das cadeias no cartão de
cada placa, grava `dK_cJ_slack_mean`/`_std_win` no CSV principal e todos os quadros em
`_dutK_chains.csv`, e confere a cadeia 0 contra o `FPGA_SENSOR`. O `verificar_hub.py` usa o
mesmo bitstream escolhido e confere as 9 cadeias em toda janela (OK na placa A, 41 janelas).

Arquivos: `.bit`, `.ltx`, `_routed.dcp` (o checkpoint deste build, para medir caminhos depois
com o `scripts/report_multi.tcl`), `_cadeias.txt`, `_timing.rpt`, `_utilization.rpt` e
`_power_{25C,Tj115}.rpt`. Todos estão só para leitura.
