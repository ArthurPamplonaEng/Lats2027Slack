# tap_top on the RV02A board (xcau15p-ffvb676-1-i). Pins as in fpga_multi_constraints.xdc
# (au15p_multi_B, validated on the bench).

# 100 MHz board oscillator, bank 64 (1.2 V)
set_property PACKAGE_PIN AD20 [get_ports sys_clk_p]
set_property PACKAGE_PIN AE20 [get_ports sys_clk_n]
set_property IOSTANDARD DIFF_SSTL12 [get_ports sys_clk_p]
set_property IOSTANDARD DIFF_SSTL12 [get_ports sys_clk_n]
create_clock -period 10.000 -name sys_clk -waveform {0.000 5.000} [get_ports sys_clk_p]

# J9 UART and button, bank 65 (1.2 V): unused, TX held idle
set_property PACKAGE_PIN Y26 [get_ports fpga_uart_tx]
set_property IOSTANDARD LVCMOS12 [get_ports fpga_uart_tx]
set_property PACKAGE_PIN W26 [get_ports fpga_uart_rx]
set_property IOSTANDARD LVCMOS12 [get_ports fpga_uart_rx]
set_property PACKAGE_PIN R26 [get_ports fpga_button]
set_property IOSTANDARD LVCMOS12 [get_ports fpga_button]

# STM32 USART1, bank 84 (3.3 V): FPGA -> STM32 held idle, STM32 -> FPGA unused (pull-up)
set_property PACKAGE_PIN W12 [get_ports mcu_usart1_rx]
set_property IOSTANDARD LVCMOS33 [get_ports mcu_usart1_rx]
set_property PACKAGE_PIN AB16 [get_ports mcu_usart1_tx]
set_property IOSTANDARD LVCMOS33 [get_ports mcu_usart1_tx]
set_property PULLTYPE PULLUP [get_ports mcu_usart1_tx]

# Status LED
set_property PACKAGE_PIN AF14 [get_ports status_o]
set_property IOSTANDARD LVCMOS33 [get_ports status_o]

# Configuration (SRAM only on the bench; the flash is never written)
set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
set_property CONFIG_MODE SPIx4 [current_design]
set_property BITSTREAM.CONFIG.CONFIGRATE 31.9 [current_design]
set_property BITSTREAM.CONFIG.USR_ACCESS TIMESTAMP [current_design]

# Unused inputs and the slow LED/UART outputs are not timed
set_false_path -from [get_ports {fpga_uart_rx fpga_button mcu_usart1_tx}]
set_false_path -to [get_ports {fpga_uart_tx mcu_usart1_rx status_o}]
