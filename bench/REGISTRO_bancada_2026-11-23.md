# Registro da bancada de 23/11/2026

Execução do [`ROTEIRO_revisao.md`](ROTEIRO_revisao.md): prioridades 0, 1 e 2 completas, mais C e D a
14 e 18 ns. Foi usada só a placa 2 (RV02A/AU15P, a de 20/11), sem forno e à temperatura ambiente. Os
números da seção "Resultados preliminares" são uma conferência, feita com
[`conferencia_2026-11-23.py`](conferencia_2026-11-23.py). Eles não substituem a análise da seção 5 do
roteiro, que ainda não foi feita.

## Campos da seção 6 do roteiro

| Campo | Valor |
|---|---|
| Data e hora de início/fim | 23/11/2026. Início às 15:28 (primeira sessão do Vivado: gravação de A e leitura de conferência). Último shmoo terminou às 17:55; `status` de fechamento às 17:56 |
| Temperatura ambiente (termômetro) | **Não medida**: não havia termômetro nesta bancada. O SYSMON leu 97 a 99 °C no die durante toda a sessão, o mesmo patamar de 20/11 (defeito conhecido do sensor da placa 2) |
| Porta do STM32 / alvo JTAG | STM32 em `/dev/ttyACM1` (o Arduino Nano 33 IoT continua em `/dev/ttyACM0` e não foi usado). JTAG via FT232H, xcau15p de DNA `40020000016069492D020285`, o mesmo de 20/11 |
| Vivado usado nos builds | **2025.2** (`~/2025.2/Vivado/bin/vivado`), o mesmo de A e B. Não é o 2025.2.1 que o roteiro supõe, porque os builds foram feitos neste PC |
| Leitura de conferência com A a 0,85 V (S70…S86) | 122,5 / 99,2 / 76,8 / 41,0 / 11,4 passos. Em 20/11: 123 / 100 / 77 / 42 / 12. Diferença ≤ 1 passo |
| Shmoos feitos (tags) | 17, na tabela abaixo |
| Anomalias | Nenhuma parada de segurança e nenhuma falha de JTAG. Uma vez o STM32 não respondeu ao comando de 0,73 V (`shmooArep`, 15:31:36, "try 1"); a segunda tentativa funcionou e o shmoo seguiu até o fim |
| Bitstream que ficou na SRAM no fim | `impl_d18` (D a 18 ns). Vcore voltou a 0,85 V: o `status` das 17:56 leu VCCINT 0,879 V (SYSMON) e 0,844 V no PMIC, sem erro nas derivações S90–S150 |

## Shmoos

Todos com `--from 0.92 --to 0.70 --back --windows 6`, programados e medidos com o mesmo `TAP_BUILD`.
O V_f é o do SYSMON, médio por derivação. As faixas abaixo são o mínimo e o máximo entre as derivações.

| Tag | Build | Período | Horário | Derivações que cruzaram a falha | V_f |
|---|---|---|---|---|---|
| `shmooArep` | `impl` | 10 ns | 15:29–15:35 | S70–S90 (6) | 0,724–0,912 V |
| `shmooA12` | `impl_a12` | 12 ns | 15:36–15:43 | S86–S106 (6) | 0,742–0,899 V |
| `shmooA14` | `impl_a14` | 14 ns | 15:43–15:52 | S98–S126 (8) | 0,733–0,920 V |
| `shmooA16` | `impl_a16` | 16 ns | 15:52–16:02 | S110–S142 (9) | 0,733–0,912 V |
| `shmooA18` | `impl_a18` | 18 ns | 16:02–16:13 | S122–S150 (8) | 0,724–0,849 V |
| `shmooB12` | `impl_b12` | 12 ns | 16:13–16:21 | S86–S106 (6) | 0,741–0,899 V |
| `shmooB14` | `impl_b14` | 14 ns | 16:21–16:29 | S98–S122 (7) | 0,725–0,899 V |
| `shmooB16` | `impl_b16` | 16 ns | 16:29–16:39 | S110–S142 (9) | 0,724–0,933 V |
| `shmooB18` | `impl_b18` | 18 ns | 16:39–16:50 | S122–S150 (8) | 0,725–0,857 V |
| `shmooC1`, `shmooC2` | `impl_c` | 10 ns | 16:50–17:03 | S70–S94 (7) | 0,724–0,920 V |
| `shmooD1`, `shmooD2` | `impl_d` | 10 ns | 17:03–17:16 | S70–S86 (5) | 0,733–0,899 V |
| `shmooC14` | `impl_c14` | 14 ns | 17:16–17:24 | S102–S130 (8) | 0,733–0,905 V |
| `shmooC18` | `impl_c18` | 18 ns | 17:24–17:36 | S130–S150 (6) | 0,724–0,808 V |
| `shmooD14` | `impl_d14` | 14 ns | 17:36–17:44 | S94–S122 (8) | 0,725–0,920 V |
| `shmooD18` | `impl_d18` | 18 ns | 17:44–17:55 | S126–S150 (7) | 0,733–0,857 V |

- Em A e B, as derivações que cruzaram são as previstas no roteiro (seção 2). A única diferença é
  S126 em B a 14 ns, que não cruzou; ela está dentro da tolerância de uma derivação e cruzou a 16 e
  a 18 ns.
- Em C e D, toda derivação de S70 a S150 cruzou em algum período, com duas exceções: S98 em C e S90
  em D, que caíram no vão entre os períodos medidos. S24 e S48 nunca cruzam, como a 10 ns.
- Ao todo são 81 derivações independentes: A 21, B 20, C 20 e D 20.

## Builds

- **Variantes de período** (`make_period.tcl`, a partir dos DCPs roteados de A, B, C e D):
  `impl_a12`…`impl_a18`, `impl_b12`…`impl_b18`, `impl_c14`, `impl_c18`, `impl_d14` e `impl_d18`.
  - Todas imprimiram `PERIOD catcher 1.750 ns` e `PERIOD done`, sem `ERROR`.
  - O timing mantém o padrão de A a 10 ns: só os 46 endpoints de max-delay das derivações longas
    falham.
  - O DRC tem as mesmas duas regras de A (PDCN-1569 e RTSTAT-10).
- **C e D** (`build.sh` com `TAP_PBLOCK` da seção 3, `-jobs 4`):
  - Saíram com o pblock certo e `TAPBUILD done`, com o mesmo padrão de timing e de DRC.
  - O WNS dos alvos de max-delay é −5,07 ns em A, −5,62 em B, −3,49 em C e −5,51 em D.
- **O Δ* não depende do período:**
  - A 12 ns, a diferença em relação a 10 ns é < 10⁻¹² ps.
  - A 14, 16 e 18 ns, a incerteza de clock sobe por igual nos caminhos de FF1 e de FF2 (+3 ps a
    14 ns, +6 ps a 18 ns) e se cancela no Δ*. Sobra no máximo 1 ps, de arredondamento do relatório.

## Previsão registrada antes da medida

- **C e D:** o commit `812b19e` (15:36) tem o `taps_sta_detail.csv` das duas implantações, e o
  primeiro shmoo de C começou às 16:50. As variantes de 14 e 18 ns herdam esse Δ*, a menos de 1 ps.
- **A e B:** as previsões das variantes de período são as de 10 ns, no repositório desde o commit
  inicial.

## Congelamento e checksums

- Os 14 bitstreams medidos foram congelados em `data/au15p_tap/build_frozen/<build>/`:
  - Cada pasta tem `tap_top.bit`, `tap_top.ltx` e `taps_sta_detail.csv`; C e D têm também
    `taps_sta.csv`.
  - O `MD5SUMS` ganhou 14 linhas, e o MD5 que o `tapbench.py` gravou no `.json` de cada um dos 17
    shmoos bate com o do bitstream congelado.
- O `data/SHA256SUMS` ganhou 78 linhas: os 34 arquivos dos shmoos e os 44 dos builds congelados.
- **Transcript do Vivado:** a linha do `vivado_transcript.log` foi trocada pelo hash atual.
  - A antiga já não batia com a versão commitada em 20/11, porque o log só cresce e foi gravado
    depois do hash.
  - Esse hash vale até o próximo comando do `tapbench.py`, que acrescenta ao log.
- `sha256sum -c` e `md5sum -c` passam inteiros.

## Resultados preliminares

O m de cada derivação é comparado com o Δ* da STA, sem nenhum parâmetro ajustado. Cada derivação entra
uma vez por implantação, com preferência pela medida de 10 ns; na falta dela, entra o menor período
que cruza.

| Conjunto | n | r | inclinação | rms(m − Δ*) | viés | melhor constante |
|---|---|---|---|---|---|---|
| 20/11, A e B a 10 ns (o do artigo hoje) | 11 | 0,84 | 0,86 | 74 ps | +36 ps | 117 ps |
| Todas as independentes (A, B, C, D) | 81 | 0,93 | 0,81 | 77 ps | 0 | 175 ps |
| Sem A-S74 | 80 | 0,93 | 0,80 | 76 ps | −1 ps | 173 ps |
| Só as novas (fora da amostra) | 70 | 0,93 | 0,81 | 77 ps | −6 ps | 182 ps |
| A e B nos períodos longos | 30 | 0,97 | 0,65 | 86 ps | +1 ps | 148 ps |
| C e D (Δ* registrado antes, em `812b19e`) | 40 | 0,94 | 0,95 | 70 ps | −10 ps | 199 ps |
| Implantação A | 21 | 0,95 | 0,62 | 97 ps | +6 ps | 148 ps |
| Implantação B | 20 | 0,93 | 0,62 | 66 ps | +15 ps | 93 ps |
| Implantação C | 20 | 0,91 | 0,77 | 69 ps | +10 ps | 135 ps |
| Implantação D | 20 | 0,95 | 0,97 | 71 ps | −31 ps | 205 ps |

- **Repetição de A:**
  - O m de 20/11 se repetiu com diferença de +3 a +19 ps por derivação (média +8 ps, menos de meio
    passo).
  - O V_f é o mesmo, a ±1 mV.
- **Resíduo |m − Δ*|:**
  - Mediana de 51 ps, percentil 90 de 128 ps e máximo de 212 ps (A S130: m = +404, Δ* = +616 ps).
  - 78 % das derivações ficam dentro de ±100 ps e 96 % dentro de ±150 ps.
  - Não há tendência com o V_f (r = −0,06 nas 81 independentes, de 0,724 a 0,933 V).
- **Δ* aponta a pior derivação:**
  - Em cada implantação, a derivação mais atrasada é a de menor Δ*: A S70 (m = −85 ps), B S118
    (−322 ps a 16 ns), C S114 (−178 ps) e D S106 (−462 ps, Δ* = −446 ps).
  - Só duas derivações saíram atrasadas com Δ* ≥ 0: B S78 (m = −61, Δ* = +10 ps) e D S150 a 18 ns
    (−55, +19 ps).

## Pontos para a análise (seção 5 do roteiro)

1. **A-S74:** a correlação deixou de depender dela. Sem A-S74, r = 0,93, e a melhor constante (173 ps)
   fica bem pior que o Δ* (76 ps).
2. **Guarda de 254 ps:** o da Seção V-C não cobre todas as derivações novas.
   - Ficam atrasadas mesmo com ele: B S118 a 16 ns (−322 ps) e D S94, S98, S102 e S106 a 14 ns (−432,
     −426, −382 e −462 ps).
   - A STA previu todas essas como atrasadas (Δ* de −307 a −446 ps).
   - A frase "254 ps excede o offset mais atrasado, de 108 ps" vale para as 11 derivações de 20/11;
     agora o mais atrasado é −462 ps.
   - Um guarda dimensionado por implantação só com a STA deixaria todas as 113 medidas seguras:
     g = −min Δ* + 2 × 74 ps, com o rms do artigo, fixado antes desta bancada.
   - Nesse caso, o menor m + g seria +273 ps em A, +164 em B, +169 em C e +132 em D.
3. **Inclinação dentro da implantação:** já não é ≈ 0,4 (o artigo dá 0,44 em A e 0,38 em B). Fica em
   0,62 em A e em B, 0,77 em C e 0,97 em D, então a frase "a STA exagera a parte de roteamento"
   enfraquece.
4. **Mesma derivação em dois períodos:** são 32 pares.
   - O m muda em média 50 ps para 103 mV de diferença no V_f. Isso é mais que a repetibilidade entre
     dias (3 a 19 ps).
   - A direção não é consistente: só 56 % dos pares andam para zero quando o V_f sobe.
   - Exemplo: A S126 dá +203, +280 e +357 ps a 14, 16 e 18 ns, com Δ* = +337 ps.
5. **Versão do Vivado:** C e D foram construídos no Vivado 2025.2, não no 2025.2.1. A seção 5 do
   roteiro foi corrigida.
