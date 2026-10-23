# program.tcl - load top.bit onto the board over USB.
#
#   vivado -mode batch -source program.tcl
#
# (Same as Hardware Manager -> Open Target -> Auto Connect -> Program Device.)

set here [file normalize [file dirname [info script]]]
open_hw_manager
connect_hw_server
open_hw_target
set dev [lindex [get_hw_devices xc7a*] 0]
current_hw_device $dev
set_property PROGRAM.FILE [file join $here top.bit] $dev
program_hw_devices $dev
close_hw_manager
