# build.tcl - Vivado batch build (non-project mode) for the generated design.
#
#   cd out
#   vivado -mode batch -source build.tcl          -> top.bit + reports
#
# Reads every .v file in this folder except testbenches (tb_*.v).
# Board: Nexys4 DDR (xc7a100tcsg324-1). Reads whichever .xdc the engine copied here.

set here [file normalize [file dirname [info script]]]
set part xc7a100tcsg324-1

foreach f [glob -directory $here *.v] {
    if {![string match tb_* [file tail $f]]} { read_verilog $f }
}
foreach x [glob -directory $here *.xdc] { read_xdc $x }

synth_design -top top -part $part
opt_design
place_design
route_design

report_utilization -hierarchical -file [file join $here utilization.rpt]
report_timing_summary -file [file join $here timing.rpt]
write_bitstream -force [file join $here top.bit]
puts "Bitstream written to [file join $here top.bit]"
