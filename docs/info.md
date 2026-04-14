## How it works

This project implements a UART-controlled servo positioning interface with a built-in sweep mode and inactivity failsafe.

At the default 25 MHz project clock, the design generates a repeating 20 ms frame on `uo[0]`.
Within each frame, the high pulse width selects the servo position:

- minimum: about 1.0 ms
- center: about 1.5 ms
- maximum: about 2.0 ms

Feature summary:

### UART preset control

The command interface is intentionally simple:

- `ui[0]` receives UART data
- digits `0` to `9` map to evenly spaced preset positions between minimum and maximum
- `c` or `C` selects the center preset
- `m` selects the minimum preset
- `M` selects the maximum preset
- `s` or `S` enables an automatic sweep mode that steps through the preset range once per frame

### Direct preset overrides

The dedicated inputs `ui[1]`, `ui[2]`, and `ui[3]` force center, minimum, and
maximum output positions. These inputs take precedence over the UART-controlled
target and give a simple hardware override path.

### Sweep/self-test mode

The sweep mode repeatedly walks the target position between minimum and maximum.
It is intended for bring-up and bench observation, where a moving output is
easier to validate than a static preset.

### Inactivity failsafe

A watchdog-style failsafe returns the output to center after a programmable
number of inactive frames. This keeps the module useful as a practical command
interface block rather than only as a waveform generator demo.

The design also exposes internal status on the regular Tiny Tapeout outputs:

- `uo[1]` toggles each time a valid UART command is received
- `uo[5:2]` shows the currently selected preset code
- `uo[6]` goes high while the failsafe mode is active
- `uo[7]` goes high while the sweep mode is active

## How to test

Drive the project with a 25 MHz clock and hold `rst_n` low during reset.

For direct input testing:

- drive `ui[1]` high to force the center servo position
- drive `ui[2]` high to force the minimum servo position
- drive `ui[3]` high to force the maximum servo position

For UART testing on `ui[0]`:

- send `m` for minimum
- send `M` for maximum
- send `c` or `C` for center
- send any digit from `0` to `9` for an intermediate preset
- send `s` or `S` to enable sweep mode

Expected outputs:

- `uo[0]` produces the servo control pulse
- `uo[1]` toggles on each accepted command
- `uo[5:2]` reflects the selected preset number
- `uo[6]` goes high when failsafe has forced the output back to center
- `uo[7]` goes high while sweep mode is running

The repository also includes a feature-oriented cocotb regression rooted at
`test/test.py`. The detailed coverage plan is documented in `verif.md`.

## External hardware

Recommended external hardware:

- a 25 MHz clock source
- a USB-to-UART adapter or microcontroller TX line connected to `ui[0]`
- a hobby servo or an oscilloscope/logic analyzer connected to `uo[0]`

The servo must be powered externally. The Tiny Tapeout output only provides the control waveform.
