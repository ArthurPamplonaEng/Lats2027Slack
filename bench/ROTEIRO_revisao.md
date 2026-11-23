# Roteiro de bancada: revisão do artigo LATS 2027

Escrito em 23/11/2026, depois do parecer. Prazo do artigo completo: **30/11/2026**.

**Objetivo:** testar fora da amostra o modelo STA da Seção V-B. Hoje a correlação (r = 0,84) depende de
uma derivação só, A-S74, cujo FF2 recebe o clock 385 ps mais tarde. Sem ela, r = 0,68, e um desvio
constante prevê melhor que o STA. Precisamos de mais derivações independentes, medidas depois de a
previsão estar registrada.

**Montagem:** só a placa 2 (RV02A/AU15P, a da bancada de 20/11), sem o forno e à temperatura
ambiente, como em 20/11. Por isso ficam fora deste roteiro o eixo de temperatura e a placa 1 (seção 7).

| Prioridade | O quê | Derivações novas | Tempo de bancada |
|---|---|---|---|
| 0 | Conexão e repetição de A a 10 ns | 0 (checa a reprodutibilidade) | ~20 min |
| 1 | A e B com período de 12, 14, 16 e 18 ns (mesmo roteamento) | até 15 em A e 15 em B | ~1 h 40 min |
| 2 | Implantações novas C e D a 10 ns | ~5 a 6 em cada | ~35 min (+20 min de build) |

Se o tempo apertar, faça nesta ordem: A14, A18, B14 e B18 (~55 min); depois C1 e D1; depois o resto.

---

## 0. Regras da bancada (não mudam)

- **Grave só a SRAM.** O `tapbench.py program` usa `program_hw_devices`. Nunca grave a flash nem use
  "Add Configuration Memory Device" no Hardware Manager.
- **Vcore só entre 0,70 e 0,92 V** (comando do PMIC; o `tapbench.py` recusa valores fora disso). No
  fim de todo shmoo, e também em erro ou Ctrl-C, o script volta a 0,85 V. Confira isso no fim
  (seção 4).
- O script para sozinho se o SYSMON ler VCCINT acima de 0,970 V, die acima de 125 °C (a placa 2 lê
  ~97 °C em ambiente, é defeito conhecido do sensor), corrente acima de 1,8 A, ou se o JTAG falhar
  três vezes seguidas. Se parar, anote a mensagem e não force.
- **Dados brutos nunca são editados.** Cada shmoo grava `data/au15p_tap/tap_<tag>_<data>.csv` com um
  `.json` ao lado. Não renomeie nem apague esses arquivos, nem os de shmoos que deram errado: anote
  no registro (seção 6).
- O `TAP_BUILD` do `program` e o do `shmoo` têm de ser **o mesmo**. O `.ltx` sai dele, e o `.json`
  registra o caminho do bitstream, que é como a análise sabe qual implantação foi medida.

## 1. Preparação (uma vez por sessão)

```bash
cd ~/Documents/Trabalho/Lats2027Slack
git fetch && git checkout revisao-parecer-2026-11-23 && git pull

# Nesta máquina o Vivado é o 2025.2.1; os scripts supõem ~/2025.2
export VIVADO_BIN=$HOME/Vivado/2025.2.1/Vivado/bin/vivado
R=$PWD/hw/au15p_tap
```

**Conexões:** cabo JTAG (FT232H) e ST-Link da placa no USB, fonte da placa ligada. Ache a porta do
STM32. Sem o Arduino do forno, ela deve ser `/dev/ttyACM0`; o padrão do script é `/dev/ttyACM1`.

```bash
ls /dev/ttyACM*
python3 -I -c "import serial; s = serial.Serial('/dev/ttyACM0', 125000, timeout=1); print(s.read(300))"
# tem de aparecer texto com "$TEL"; se não aparecer, tente a outra porta
STM=/dev/ttyACM0
```

**Programe A (10 ns) e confira a leitura:**

```bash
TAP_BUILD=$R/build/impl python3 -I bench/tapbench.py program --stm $STM
```

O script imprime uma janela. Com o PMIC em 0,85 V (SYSMON ≈ 0,879 V), em 20/11 a implantação A leu:

| | S70 | S74 | S78 | S82 | S86 | S90 |
|---|---|---|---|---|---|---|
| A (20/11) | 123 | 100 | 77 | 42 | 12 | erro |
| B (20/11) | 132 | 94 | 67 | 35 | 14 | erro |

A diferença deve ficar em ±3 passos. Se a leitura estiver muito diferente, pare e anote: pode ser
outra placa, outro bitstream ou a tensão fora do lugar.

**Repetição de A a 10 ns** (~8 min). Mostra que nada mudou desde 20/11 e que este PC e este Vivado
medem igual:

```bash
TAP_BUILD=$R/build/impl python3 -I bench/tapbench.py shmoo --from 0.92 --to 0.70 --back --windows 6 --tag shmooArep --stm $STM
```

Espera-se o mesmo V_f da Tabela I: S70 e S74 em 0,725, S78 em 0,774, S82 em 0,816, S86 em 0,857 e
S90 em 0,912 V (SYSMON), com diferença de no máximo um degrau de 10 mV. Cada linha do log mostra
`taps-with-errors N` e a leitura de cada derivação; `*` marca as que tiveram erro.

## 2. Prioridade 1: mesmo roteamento, período maior (A e B)

**Por quê:** a 10 ns, as derivações S94–S150 já falham no topo da faixa e nunca foram medidas. Com
período maior, a fronteira de falha passa por elas. O roteamento continua o de A e de B, então a
previsão de cada uma já está no repositório, registrada antes da medida. O Δ* não depende do
período: testei em A a 12 ns e as 23 derivações dão o mesmo Δ* de 10 ns, com diferença menor que
10⁻¹² ps. As previsões variam bastante e incluem casos difíceis:

| S | 94 | 98 | 102 | 106 | 110 | 114 | 118 | 122 | 126 | 130 | 134 | 138 | 142 | 146 | 150 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Δ* em A (ps) | +18 | −88 | −10 | +10 | −176 | +6 | +294 | +64 | +337 | +616 | +46 | +385 | +104 | +490 | +404 |
| Δ* em B (ps) | −2 | +8 | −330 | +55 | −82 | −155 | −337 | −84 | −68 | +226 | +64 | −184 | +82 | +164 | −40 |

Só os divisores do MMCM mudam. O VCO continua em 1 GHz, e o passo fino continua 17,857 ps. O catcher
mantém 1,75 ns depois do clock do sistema (o DRC não aceita 63° fora do período de 10 ns, e o script
já resolve isso). A janela de 10⁸ ciclos passa a durar T/10 s, ou seja, 1,2 a 1,8 s.

**Derivações que devem cruzar a falha entre 0,92 e 0,70 V** (estimativa a partir de 20/11, com erro
de uma derivação para cada lado):

| Período (DIVIDE) | 12 ns | 14 ns | 16 ns | 18 ns |
|---|---|---|---|---|
| Derivações | S86–S106 | S98–S126 | S110–S142 | S122–S150 |

A sobreposição é proposital. S86 e S90 medidas a 12 ns repetem a medida de 10 ns e testam, na
prática, se o desvio independe do período.

**2a. Gerar os bitstreams** (~1 a 2 min cada; dá para fazer antes de ligar a placa):

```bash
for P in a b; do
  SRC=$R/build/impl; [ $P = b ] && SRC=$R/build/impl_b
  for D in 12 14 16 18; do
    OUT=$R/build/impl_$P$D                     # impl_a12, impl_a14, ..., impl_b18
    mkdir -p $OUT
    $VIVADO_BIN -mode batch -nojournal -log $OUT/period.log \
      -source $R/scripts/make_period.tcl -tclargs $SRC/tap_top_routed.dcp $OUT $D
    $VIVADO_BIN -mode batch -nojournal -nolog \
      -source $R/scripts/report_taps_detail.tcl -tclargs $OUT/tap_top_routed.dcp $OUT/taps_sta_detail.csv
    grep -E "PERIOD (catcher|done)|ERROR" $OUT/period.log
  done
done
```

Para cada um tem de aparecer `PERIOD catcher 1.750 ns ...` e `PERIOD done`, sem `ERROR`. O
`timing_summary.rpt` mostra 46 endpoints falhando (WNS ≈ −5,07 ns): são os alvos de max-delay das
derivações longas, que falham de propósito. Isso é igual em A a 10 ns e não é problema.

**2b. Medir.** Um shmoo por período e por implantação. Leva ~10 min a 12 ns e ~15 min a 18 ns.

```bash
for D in 12 14 16 18; do
  TAP_BUILD=$R/build/impl_a$D python3 -I bench/tapbench.py program --stm $STM
  TAP_BUILD=$R/build/impl_a$D python3 -I bench/tapbench.py shmoo --from 0.92 --to 0.70 --back --windows 6 --tag shmooA$D --stm $STM
done
for D in 12 14 16 18; do
  TAP_BUILD=$R/build/impl_b$D python3 -I bench/tapbench.py program --stm $STM
  TAP_BUILD=$R/build/impl_b$D python3 -I bench/tapbench.py shmoo --from 0.92 --to 0.70 --back --windows 6 --tag shmooB$D --stm $STM
done
```

**Durante a medida:**
- No topo (0,92 V), as derivações da tabela acima não podem ter `*`. Embaixo (0,70 V), devem ter.
- As derivações curtas podem não alarmar em períodos longos, porque a folga passa dos 440 passos
  (7,86 ns). É esperado: a varredura vai até o fim e o número de varreduras por segundo cai.
- Se uma derivação da tabela já falhar no topo, ou não falhar embaixo, anote. O período vizinho
  cobre.

## 3. Prioridade 2: implantações C e D

**Por quê:** são roteamentos novos da mesma RTL, em regiões de clock que A e B não usam. O xcau15p
tem 2 × 3 regiões: A ocupa X0Y1/X1Y1, B fica em X0Y2, e X1Y0 e X1Y2 estão vazias (1380 slices cada,
sem buracos). O pblock tem o mesmo tamanho do de A (16 × 50 slices).

| Implantação | Região | Pblock (`TAP_PBLOCK`) |
|---|---|---|
| C | X1Y0 | `SLICE_X34Y5:SLICE_X49Y54` |
| D | X1Y2 | `SLICE_X34Y125:SLICE_X49Y174` |
| reserva, se C ou D falhar no place | X0Y0 (tem o MMCM) | `SLICE_X8Y5:SLICE_X23Y54` |

**3a. Build** (~10 min cada; pode rodar enquanto a placa mede a prioridade 1):

```bash
mkdir -p $R/build/impl_c $R/build/impl_d
TAP_PBLOCK=SLICE_X34Y5:SLICE_X49Y54    $R/scripts/build.sh $R/build/impl_c
TAP_PBLOCK=SLICE_X34Y125:SLICE_X49Y174 $R/scripts/build.sh $R/build/impl_d
for X in c d; do
  $VIVADO_BIN -mode batch -nojournal -nolog -source $R/scripts/report_taps_detail.tcl \
    -tclargs $R/build/impl_$X/tap_top_routed.dcp $R/build/impl_$X/taps_sta_detail.csv
  grep -E "TAPIMPL pblock|TAPBUILD done" $R/build/impl_$X/build.log
done
```

Confira que o log mostra o pblock certo e `TAPBUILD done`, e que o `timing_summary.rpt` tem o mesmo
padrão de A: só os 46 endpoints de max-delay das derivações longas falham; os clocks c0 e c1 e os
caminhos do sensor passam.

**3b. Registre a previsão antes de medir.** Isso torna o teste fora da amostra verificável:

```bash
git add $R/build/impl_c/taps_sta_detail.csv $R/build/impl_c/taps_sta.csv \
        $R/build/impl_d/taps_sta_detail.csv $R/build/impl_d/taps_sta.csv
git commit -m "Previsões STA das implantações C e D, registradas antes da bancada" && git push
```

**3c. Medir:** dois shmoos de cada, como B em 20/11 (~8 min cada).

```bash
for X in c d; do
  T=$(echo $X | tr a-z A-Z)
  TAP_BUILD=$R/build/impl_$X python3 -I bench/tapbench.py program --stm $STM
  for k in 1 2; do
    TAP_BUILD=$R/build/impl_$X python3 -I bench/tapbench.py shmoo --from 0.92 --to 0.70 --back --windows 6 --tag shmoo$T$k --stm $STM
  done
done
```

Se sobrar tempo: C e D também a 14 e 18 ns, com o `make_period.tcl` da seção 2a, saídas
`impl_c14`, `impl_c18` etc. e tags `shmooC14`, `shmooC18` etc.

## 4. Fechamento da sessão

```bash
# a placa tem de estar em 0,85 V (SYSMON ≈ 0,879 V); use o TAP_BUILD do último bitstream gravado
TAP_BUILD=$R/build/impl_d python3 -I bench/tapbench.py status --stm $STM
```

O bitstream fica na SRAM até desligar a placa. Ao religar, volta o design da flash, que nunca foi
gravada. Anote qual bitstream ficou.

**Congelar os bitstreams medidos e registrar os checksums** (rode **uma vez só**: os dois comandos
acrescentam linhas, e uma segunda execução duplicaria as entradas):

```bash
for d in impl_a12 impl_a14 impl_a16 impl_a18 impl_b12 impl_b14 impl_b16 impl_b18 impl_c impl_d; do
  [ -f $R/build/$d/tap_top.bit ] || continue
  mkdir -p data/au15p_tap/build_frozen/$d
  cp $R/build/$d/{tap_top.bit,tap_top.ltx,taps_sta_detail.csv} data/au15p_tap/build_frozen/$d/
  (cd data/au15p_tap/build_frozen && md5sum $d/tap_top.bit >> MD5SUMS)
done
# SHA-256 de todo arquivo novo em data/ (shmoos, .json e bitstreams congelados)
git ls-files --others --exclude-standard -- data | sed 's|^data/|./|' | (cd data && xargs sha256sum) >> data/SHA256SUMS
```

**Commit e push:**

```bash
git add data/
for d in $R/build/impl_c $R/build/impl_d; do [ -d $d ] && git add $d; done
for d in $R/build/impl_[ab]1[2468]; do          # só as variantes de período que foram feitas
  [ -d $d ] && git add $d/{period.log,timing_summary.rpt,drc.rpt,taps_sta_detail.csv,tap_top.bit,tap_top.ltx}
done
git commit -m "Bancada de <data>: período 12-18 ns em A e B, implantações C e D" && git push
```

O `tap_top_routed.dcp` das variantes de período não precisa ir para o git, porque o
`make_period.tcl` o refaz a partir do DCP de A ou de B.

## 5. O que muda na análise (eu faço quando os dados chegarem)

**Feito em 23/11/2026**, depois da bancada: ver o `PLANO.md` e o artigo. Diferenças em relação ao
plano abaixo: a Tabela I continua por derivação (sessão de 20/11, com as guardas) e o resumo por
conjunto virou a Tabela II; o conjunto independente usa o menor período em que cada derivação cruza
a falha (o maior período dá 69 ps rms, em vez de 77).

- **`analysis/tap_offsets.py`:** acrescentar ao `IMPLS` as entradas `impl_a12`…`impl_b18`, `impl_c` e
  `impl_d`. O `impl_of()` reconhece a implantação pelo `/build/<pasta>/` gravado no `.json`.
- **`analysis/tap_values.py`:**
  - o conjunto independente passa a ser A, B, C e D, mais as derivações dos períodos longos que não
    foram medidas a 10 ns. Cada derivação conta uma vez por implantação, com preferência para a
    medida de 10 ns;
  - as derivações medidas em dois períodos (S86–S90 a 12 ns e as sobreposições entre períodos)
    viram o teste "m não depende de T";
  - o modelo segue sem parâmetro ajustado. Reporto o rms e o r sem A-S74, o leave-one-out e o rms
    de C, D e das derivações longas em separado, como teste fora da amostra.
- **Artigo:**
  - a Tabela I fica grande demais e vira resumo por implantação, com os valores por derivação no
    repositório;
  - a Fig. 3 ganha os pontos novos;
  - a Seção V-B e as Limitações são reescritas com o n novo;
  - registrar que C e D foram construídos no Vivado 2025.2, o mesmo de A e B (não no 2025.2.1; ver
    o registro de 23/11).
- A repetição `shmooArep` entra na repetibilidade de A (dias diferentes).

## 6. Registro da sessão (preencher)

Sessão de 23/11/2026. O detalhe, com horários, builds, checksums e números preliminares, está em
[`REGISTRO_bancada_2026-11-23.md`](REGISTRO_bancada_2026-11-23.md).

| Campo | Valor |
|---|---|
| Data e hora de início/fim | 23/11/2026, 15:28 a 17:56 |
| Temperatura ambiente (termômetro, não o SYSMON) | não medida (sem termômetro); die 97–99 °C no SYSMON, como em 20/11 |
| Porta do STM32 / alvo JTAG | `/dev/ttyACM1` / FT232H, DNA `40020000016069492D020285` (placa 2) |
| Vivado usado nos builds | 2025.2 (não 2025.2.1) |
| Leitura de conferência com A a 0,85 V (S70…S86) | 122,5 / 99,2 / 76,8 / 41,0 / 11,4 |
| Shmoos feitos (tags) | `shmooArep`; `shmooA12`, `A14`, `A16`, `A18`; `shmooB12`, `B14`, `B16`, `B18`; `shmooC1`, `C2`, `D1`, `D2`; `shmooC14`, `C18`, `D14`, `D18` |
| Anomalias (paradas de segurança, JTAG, saltos de leitura) | nenhuma parada nem falha de JTAG; o STM32 não respondeu uma vez a 0,73 V (`shmooArep`) e respondeu na segunda tentativa |
| Bitstream que ficou na SRAM no fim | `impl_d18`, com Vcore em 0,85 V (VCCINT 0,879 V) |

## 7. Fora deste roteiro

- **Eixo de temperatura:** depende do forno e do PID regravado no Nano 33 IoT. Fica para quando o
  forno estiver ligado.
- **Placa 1:** só a placa 2 está conectada. Repetir A e B na placa 1 separaria o efeito do dispositivo.
- **Derivações mais densas (S60–S96 de 2 em 2):** não recomendo agora. A prioridade 1 já dá até 30
  derivações novas sem mexer na RTL. Mudar o passo exigiria alterar a lista de estágios em
  `rtl/tap_pkg.sv`, `constr/tap_impl.tcl`, `scripts/make_guard.tcl`, `bench/tapbench.py` e
  `analysis/tap_analysis.py`, e refazer os builds.

## 8. Se algo der errado

| Sintoma | Provável causa | O que fazer |
|---|---|---|
| `program` não acha alvo JTAG | cabo, fonte da placa ou `hw_server` preso | religar o cabo; `pkill hw_server`; tentar de novo |
| `attach` falha (VIO não encontrado) | `TAP_BUILD` diferente do bitstream gravado | rodar `program` com o mesmo `TAP_BUILD` |
| Sem `$TEL` na porta | porta errada (ACM0/ACM1) | testar a outra; conferir o ST-Link |
| Leitura de A a 0,85 V muito diferente da tabela | placa, bitstream ou tensão | parar e anotar; não seguir com períodos |
| Parada de segurança (VCCINT, T, I, JTAG) | condição real ou leitura ruim | anotar a mensagem; conferir 0,85 V com `status` |
| Ctrl-C no meio do shmoo | — | o script volta a 0,85 V; conferir com `status`; o CSV parcial fica (não apagar) |
