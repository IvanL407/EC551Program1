# EC551 Program 1 - Logic Synthesis Engine

EC551 Advanced Digital Design with Verilog and FPGAs, Fall 2026, Prof. Densmore

Team: Vinayak M., Ivan

## What this project does

This is a Python program that takes either a Boolean function (for example F = A'B + AC) or a digital logic circuit (a list of gates and the wires between them) and:

- shows the canonical SOP and POS forms, and the same forms for the inverse F'

- makes the function as small as possible (minimized SOP and POS) and tells you how many literals were saved

- counts the prime implicants, essential prime implicants, ON-set minterms and OFF-set maxterms

- has two extra commands of our own: a truth table exporter and a static-1 hazard checker

- turns the minimized function into a structural Verilog file (only not, and, or and buf gates) that can be loaded onto the Nexys4 DDR FPGA board

## What you need

| Tool | Why | Notes |
|---|---|---|
| Python 3.8 or newer | runs the whole program | no extra packages needed |
| Icarus Verilog (iverilog) | to simulate the Verilog on your laptop | optional, Vivado's simulator also works |
| Vivado | to build and load the design onto the board | on Windows, use the Vivado Tcl shell |
| Nexys4 DDR board | for the live demo | FPGA part xc7a100tcsg324-1 |

## Files in this project

| File | What it does |
|---|---|
| synth.py | the main program you run, with all 12 commands |
| inputs.py | reads the function you type or the file you give it |
| parse.py | turns the expression into a truth table |
| canonical.py | canonical SOP/POS, the inverse forms, and the ON/OFF-set counts (items 1-4, 9, 10) |
| qm.py | finds all prime implicants using the Quine-McCluskey method (item 7) |
| cover.py | finds the essential primes and picks the cheapest set of primes (items 5, 6, 8) |
| minimize.py | writes the minimized SOP/POS as text and counts the literals (items 5, 6) |
| custom.py | our two custom commands: truth table export and hazard check (items 11, 12) |
| circuit.py | reads a logic circuit file (.bench) and runs the same 12 commands on it |
| verilog.py | writes the structural Verilog, a testbench and the board files |
| check.py | tests the main program |
| check_verilog.py | tests the Verilog that verilog.py makes |
| check_circuit.py | tests the circuit input |
| tests folder | example inputs for the demo: 2 functions (.eqn) and 3 circuits (.bench) |
| seg7_mux.v | drives the 7-segment display on the board |
| Nexys4DDR_Master.xdc | the course pin file, not changed (used in basic mode) |
| Nexys4DDR_full.xdc | the same pin file with more pins turned on (used in full mode) |
| build.tcl | Vivado script that builds the bitstream (top.bit) |
| program.tcl | Vivado script that loads top.bit onto the board |

## How it works

1. You give the program a function (typed in or from a file) or a circuit file.

2. The program turns it into a truth table: a list with one 0 or 1 for every input combination. For a function, it works out the expression for every input combination. For a circuit, it puts the gates in order (each gate after the gates that feed it) and simulates the circuit for every input combination. Every command after this works from that truth table, so it does not matter which kind of input was used.

3. The canonical forms come straight from the truth table. The rows where F = 1 give the SOP, and the rows where F = 0 give the POS.

4. To minimize, qm.py keeps joining terms that differ in only one variable (for example A'BC' + A'BC = A'B) until nothing more can be joined. The terms that are left are the prime implicants.

5. cover.py always keeps the essential primes (a prime is essential if it is the only one that covers some minterm). For the minterms that are still not covered, it searches for the choice with the fewest literals.

6. For the minimized POS, we minimize F' as an SOP and then flip it with DeMorgan's law. So the same code does both SOP and POS.

7. The hazard check looks at every pair of input patterns where F = 1 that differ in just one input. If no single product term covers both, the output could glitch when that input changes. The program lists these pairs and shows a fixed cover with the extra terms added.

8. verilog.py turns the minimized answer into gates: one NOT gate for each variable that appears with a ', one AND gate for each product term, and one OR gate to join them (for POS, it is OR gates first and then one AND gate). A few small rules keep the circuit simple:

- the NOT gate for a variable is shared by every term that needs it

- a term with only one literal (like just A) does not need a gate, so its wire is used directly

- if the function is always 0 or always 1, the output is just a buf gate tied to 0 or 1

- every wire and gate name the program makes up has an underscore in it (like A_n or p_0). Variable names cannot have an underscore, so they never clash.

## How to use the program

### Ways to write a function

| You type | What it means |
|---|---|
| A'B + AC | just the expression (variables are put in alphabetical order) |
| F = A'B + AC | the same, with a name |
| F(A,B,C) = A'B + AC | you choose the variables and their order |
| F(A,B,C) = m(2,3,5,7) | list of minterms (rows where F is 1) |
| F(A,B,C) = M(0,1,4,6) | list of maxterms (rows where F is 0) |

| Symbol | Meaning |
|---|---|
| + | OR |
| \* or two letters side by side (AB) | AND |
| ' after a variable, or ! before it | NOT |
| ( ) | brackets |

Variable names are one letter, with numbers after it if you want (A, B, x1, x2). For names with numbers, put \* between them, like x1\*x2. You can use up to 16 variables.

You can also save the function in a text file with one line in it, like the example files in the tests folder. For example, tests/example1.eqn contains:

F(A,B,C,D) = m(0,2,5,7,8,10,13,15)

### Running the program

Run all 12 commands on a function:

python3 synth.py -e "F = A'B + AC" -c all

Run only some commands:

python3 synth.py -e "F = A'B + AC" -c msop -c mpos -c pi

Use a file instead of typing the function:

python3 synth.py tests/example1.eqn -c all

Or start the program with no commands, and then type commands one at a time:

python3 synth.py

Then type, for example: expr F = A'B + AC, then msop, then quit.

### Giving it a circuit

A circuit is written in the .bench format, which is a standard format for gate-level circuits. Each line is one gate, and its inputs are the wires coming into it. For example, tests/mux.bench is a 2-to-1 multiplexer made only of NAND gates:

INPUT(S)

INPUT(A)

INPUT(B)

OUTPUT(F)

Sn = NAND(S, S)

n1 = NAND(A, Sn)

n2 = NAND(B, S)

F = NAND(n1, n2)

The rules:

- INPUT(name) and OUTPUT(name) list the inputs and outputs. The first INPUT is the most significant bit, like the first variable in F(A,B,C).

- each gate line is: wire name = GATE(input wires). The gates you can use are AND, OR, NOT, NAND, NOR, XOR, XNOR and BUF.

- the lines can be in any order, and a hash sign starts a comment

- input and output names are a letter followed by letters or numbers (for example A, S, A1, Cin)

- the program gives a clear error if a wire is never defined, a gate has the wrong number of inputs, or the circuit loops back on itself (then it is not combinational)

Run all 12 commands on a circuit:

python3 circuit.py tests/mux.bench -c all

Or leave out -c all to type commands one at a time, the same as with synth.py. When it loads, it also prints the size of the circuit (for example: 3 inputs, 1 output, 4 gates, depth 3).

If a circuit has more than one output, pick which one to look at with --output:

python3 circuit.py tests/adder.bench --output Cout -c all

### Example inputs for the demo

| File | Type | What it shows |
|---|---|---|
| tests/example1.eqn | function | F(A,B,C,D) = m(0,2,5,7,8,10,13,15). 32 literals become just B'D' + BD. |
| tests/hazard.eqn | function | F = A'B + AC + BC. msop removes the extra BC, and hazard shows BC is the term that stops the glitch. |
| tests/mux.bench | circuit | 2-to-1 mux made of 4 NAND gates. Becomes S'A + SB, and has the classic mux hazard. |
| tests/compare.bench | circuit | 2-bit comparator (is A1A0 bigger than B1B0?), 4 inputs and 6 gates |
| tests/adder.bench | circuit | 1-bit full adder with 2 outputs, S and Cout. S is XOR, which cannot be made smaller. |

### List of commands

| Command | Item | What it shows |
|---|---|---|
| csop | 1 | canonical SOP |
| cpos | 2 | canonical POS |
| icsop | 3 | canonical SOP of the inverse F' |
| icpos | 4 | canonical POS of the inverse F' |
| msop | 5 | minimized SOP, and literals saved compared to the canonical SOP |
| mpos | 6 | minimized POS, and literals saved compared to the canonical POS |
| pi | 7 | number of prime implicants |
| epi | 8 | number of essential prime implicants |
| minterms | 9 | number of ON-set minterms |
| maxterms | 10 | number of OFF-set maxterms |
| tt | 11 | custom command 1: prints the truth table (tt table.csv saves it as a CSV file) |
| hazard | 12 | custom command 2: finds static-1 hazards and shows a hazard-free version |
| all | | runs items 1 to 12 |
| load (file) | | loads a function from a file |
| expr (function) | | types in a new function |
| help, quit | | |

### Example

For F = A'B + AC the program shows (some lines are left out here):

| Item | Result |
|---|---|
| 1. canonical SOP | A'BC' + A'BC + AB'C + ABC |
| 5. minimized SOP | A'B + AC, 12 literals down to 4 (8 saved) |
| 6. minimized POS | (A + B)(A' + C), 12 literals down to 4 (8 saved) |
| 7. prime implicants | 3 (BC, A'B, AC) |
| 8. essential prime implicants | 2 (A'B, AC) |
| 9. ON-set minterms | 4, which are m(2,3,5,7) |
| 10. OFF-set maxterms | 4, which are M(0,1,4,6) |
| 12. hazards | 1 hazard when A changes between 011 and 111. Fixed version: BC + A'B + AC |

## Making the Verilog

Run verilog.py with the same kind of input:

python3 verilog.py -e "F = A'B + AC"

This makes the SOP circuit in full board mode and saves everything in a folder called out. You can change this:

- add --form pos to make the POS circuit instead of the SOP one

- add --mode basic to use the course pin file exactly as given (see Board modes below)

- add --out (folder name) to save to a different folder

For example:

python3 verilog.py -e "F = A'B + AC" --form pos --mode basic --out out

It works with files too, both functions and circuits:

python3 verilog.py tests/hazard.eqn

python3 verilog.py tests/compare.bench

python3 verilog.py tests/adder.bench --output Cout

The out folder will have:

| File | What it is |
|---|---|
| F_sop.v (or F_pos.v) | the circuit made of gates. The name follows your function name and form. |
| tb_F_sop.v | a testbench that tries every input and checks the answer |
| top.v | connects the circuit to the switches, LEDs and display |
| seg7_mux.v | the display driver (full mode only) |
| one .xdc file | the pin file for the mode you picked |
| build.tcl and program.tcl | the Vivado scripts |

The first three files are made fresh by verilog.py every time. The rest are copied from the main project folder: seg7_mux.v, build.tcl and program.tcl were written by us, Nexys4DDR_Master.xdc is the course file, and Nexys4DDR_full.xdc is the course file with more pins turned on.

For F = A'B + AC the circuit has 4 gates: 1 NOT gate (makes A'), 2 AND gates (make A'B and AC) and 1 OR gate (joins them into F).

## Board modes

Both modes use the pin names from the course file Nexys4DDR_Master.xdc.

Basic mode uses the course pin file exactly as given. It only turns on 8 switches and 8 LEDs, so it works for up to 8 inputs.

| On the board | What it shows |
|---|---|
| switches | the inputs. The first variable is on the highest switch used, and the last variable is on switch 0. |
| LED 7 | the output F |
| LEDs 0 to 6 | which input switches are on |

Full mode (the default) uses Nexys4DDR_full.xdc. This is the same file with more lines turned on: the clock, switches and LEDs 8 to 15, the RGB LED and the 7-segment display. It works for up to 16 inputs.

| On the board | What it shows |
|---|---|
| switches | the inputs (same order as basic mode) |
| LEDs | which input switches are on |
| RGB LED | green when F = 1, red when F = 0 |
| 7-segment, left side | the minterm number for the current switches |
| 7-segment, right side | the letter F and the output value (0 or 1) |

## Testing in simulation

Go into the out folder and run:

cd out

iverilog -o sim F_sop.v tb_F_sop.v

vvp sim

If the circuit is right, you will see: PASS F_sop: all 8 input patterns match.

If a gate were wrong, you would see FAIL lines that tell you which input gave the wrong answer.

You can also do this in Vivado: add tb_F_sop.v as a simulation source and click Run Simulation. The PASS line shows up in the Tcl console.

## Putting it on the FPGA

### Step 1: build

From inside the out folder, run:

vivado -mode batch -source build.tcl

This makes top.bit. It also makes utilization.rpt and timing.rpt if you want to see how much of the FPGA was used.

If you would rather use the Vivado window:

1. Make a new RTL project with the part xc7a100tcsg324-1 (or pick the Nexys4 DDR board).

2. Add F_sop.v and top.v as design sources. In full mode, also add seg7_mux.v. Do not add the testbench (tb_F_sop.v) as a design source.

3. Add the .xdc file from the out folder as the constraint file. Only add this one. The main project folder has both .xdc files, and using both can cause errors.

4. Check that top is the top module, then click Generate Bitstream.

5. To see your gates, open RTL Analysis, then Schematic, and look inside the block called core.

### Step 2: program the board

Plug the board in with the USB cable and turn it on. Then run:

vivado -mode batch -source program.tcl

Or in the Vivado window: Open Hardware Manager, then Open Target, then Auto Connect, then Program Device.

### Step 3: check it works

For F = A'B + AC, input A is on switch 2, B is on switch 1 and C is on switch 0. F should be 1 for minterms 2, 3, 5 and 7.

| Switch 2, 1, 0 | Minterm | F | Basic mode: LED 7 | Full mode: RGB LED | Full mode: display |
|---|---|---|---|---|---|
| 0 0 0 | 0 | 0 | off | red | 0 ... F0 |
| 0 0 1 | 1 | 0 | off | red | 1 ... F0 |
| 0 1 0 | 2 | 1 | on | green | 2 ... F1 |
| 0 1 1 | 3 | 1 | on | green | 3 ... F1 |
| 1 0 0 | 4 | 0 | off | red | 4 ... F0 |
| 1 0 1 | 5 | 1 | on | green | 5 ... F1 |
| 1 1 0 | 6 | 0 | off | red | 6 ... F0 |
| 1 1 1 | 7 | 1 | on | green | 7 ... F1 |

This should match the truth table from the tt command.

## Self tests

Run these from the main project folder:

python3 check.py

python3 check_verilog.py

python3 check_circuit.py

- check.py checks the main program against answers worked out by hand. Then it makes 300 random functions and checks that every answer the program prints really means the same function.

- check_verilog.py makes the Verilog for 48 functions (special cases like F = A, F = A + A' and F = AA', plus 40 random ones), as both SOP and POS. It simulates each one with its testbench. This one needs iverilog.

- check_circuit.py checks the example circuits against answers worked out by hand. Then it makes 300 random circuits and checks that each one gives the same truth table as the same logic written as an expression. It also checks that broken circuit files give a clear error message, and simulates the Verilog made from the example circuits.

All three should finish with ALL CHECKS PASSED (or ALL VERILOG / ALL CIRCUIT CHECKS PASSED).

## Limits

- Up to 16 input variables (the board has 16 switches). Basic mode allows up to 8.

- Big functions are slow to minimize. Up to about 8 variables is instant, 10 variables takes a few seconds, and 12 or more can take minutes. For the demo, use functions with 3 to 8 variables.

- Very long answers are cut short on screen. Use tt table.csv to save the full truth table.

- Only one output at a time. For a circuit with several outputs, pick one with --output.



## Use of AI tools
Following the course AI policy, parts of this project were AI-assisted. We used Claude (by Anthropic) to help write and debug some of the code. All design decisions were ours. We reviewed every AI-assisted part, tested it with check.py and check_verilog.py, and checked that it meets the assignment requirements. We understand how all of the code works and can explain it during the demo.
