import cocotb
from cocotb.triggers import ClockCycles

from verification.common import (
    INVALID_COMMANDS,
    ack_bit,
    apply_override,
    apply_uart_command,
    current_status,
    digit_pulse,
    drive_to_failsafe,
    failsafe_active,
    initialize_test,
    measure_pulses,
    preset_code,
    release_overrides,
    sweep_active,
)


@cocotb.test()
async def test_uart_digit_walks_full_range(dut):
    cfg = await initialize_test(dut, "Integration UART full-range walk")
    previous_ack = ack_bit(dut)

    for digit in range(10):
        observation = await apply_uart_command(dut, cfg, str(digit), measure_pulse=not cfg.gate_level)
        assert preset_code(dut) == digit, f"digit {digit} left preset code {preset_code(dut)}"
        assert ack_bit(dut) != previous_ack, f"digit {digit} did not toggle ack"
        if observation.pulse_width is not None:
            assert observation.pulse_width == digit_pulse(cfg, digit), f"digit {digit} produced {observation.pulse_width}"
        previous_ack = ack_bit(dut)


@cocotb.test()
async def test_invalid_command_noise_does_not_disturb_last_valid_uart_state(dut):
    cfg = await initialize_test(dut, "Integration invalid command noise rejection")

    observation = await apply_uart_command(dut, cfg, "7", measure_pulse=not cfg.gate_level)
    assert preset_code(dut) == 7, f"expected preset 7 after valid command, got {preset_code(dut)}"
    if observation.pulse_width is not None:
        assert observation.pulse_width == digit_pulse(cfg, 7), f"digit 7 pulse was {observation.pulse_width}"

    stable_ack = ack_bit(dut)
    for invalid_char in INVALID_COMMANDS:
        observation = await apply_uart_command(dut, cfg, invalid_char, measure_pulse=not cfg.gate_level)
        assert ack_bit(dut) == stable_ack, f"invalid command {invalid_char!r} toggled ack"
        assert preset_code(dut) == 7, f"invalid command {invalid_char!r} changed preset code to {preset_code(dut)}"
        if observation.pulse_width is not None:
            assert observation.pulse_width == digit_pulse(cfg, 7), f"invalid command {invalid_char!r} changed pulse"


@cocotb.test()
async def test_sweep_override_and_uart_recovery_flow(dut):
    cfg = await initialize_test(dut, "Integration sweep override recovery")

    await apply_uart_command(dut, cfg, "s")
    assert sweep_active(dut) == 1, "sweep should be active after command"

    observation = await apply_override(dut, cfg, maximum=True, measure_pulse=not cfg.gate_level)
    assert sweep_active(dut) == 0, "override should cancel sweep"
    assert preset_code(dut) == 9, f"maximum override produced preset {preset_code(dut)}"
    if observation.pulse_width is not None:
        assert observation.pulse_width == cfg.max_pulse_cycles, f"maximum override produced {observation.pulse_width}"

    await release_overrides(dut)
    observation = await apply_uart_command(dut, cfg, "c", measure_pulse=not cfg.gate_level)
    assert preset_code(dut) == 5, f"center command after override produced preset {preset_code(dut)}"
    assert sweep_active(dut) == 0, "center command should keep sweep disabled"
    if observation.pulse_width is not None:
        assert observation.pulse_width == cfg.center_pulse_cycles, f"center command produced {observation.pulse_width}"


@cocotb.test()
async def test_failsafe_recovery_then_sweep_enable_flow(dut):
    cfg = await initialize_test(dut, "Integration failsafe recovery and sweep")
    if cfg.gate_level:
        dut._log.info("Skipping long failsafe recovery flow in gate-level mode")
        return

    await apply_uart_command(dut, cfg, "M", measure_pulse=True)
    await drive_to_failsafe(dut, cfg)
    assert failsafe_active(dut) == 1, "failsafe did not assert"

    observation = await apply_uart_command(dut, cfg, "2", measure_pulse=True)
    assert failsafe_active(dut) == 0, "digit command should clear failsafe"
    assert preset_code(dut) == 2, f"digit 2 produced preset {preset_code(dut)}"
    assert observation.pulse_width == digit_pulse(cfg, 2), f"digit 2 produced {observation.pulse_width}"

    await apply_uart_command(dut, cfg, "s")
    assert sweep_active(dut) == 1, "sweep should enable after failsafe recovery"


@cocotb.test()
async def test_reset_restores_defaults_after_activity_mix(dut):
    cfg = await initialize_test(dut, "Integration reset after mixed activity")
    if cfg.gate_level:
        dut._log.info("Skipping mixed-activity reset flow in gate-level mode")
        return

    await apply_uart_command(dut, cfg, "9", measure_pulse=True)
    await apply_uart_command(dut, cfg, "s")
    await ClockCycles(dut.clk, 2)
    await apply_override(dut, cfg, minimum=True, measure_pulse=True)

    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)

    assert current_status(dut) == {"ack": 0, "preset": 5, "failsafe": 0, "sweep": 0}, f"reset left status {current_status(dut)}"


@cocotb.test()
async def test_keepalive_command_postpones_failsafe_until_later(dut):
    cfg = await initialize_test(dut, "Integration failsafe keepalive timing")
    if cfg.gate_level:
        dut._log.info("Skipping keepalive timing flow in gate-level mode")
        return

    await apply_uart_command(dut, cfg, "M", measure_pulse=True)
    await drive_to_failsafe(dut, cfg)
    assert failsafe_active(dut) == 1, "baseline timeout did not assert failsafe"

    await apply_uart_command(dut, cfg, "M", measure_pulse=True)
    await ClockCycles(dut.clk, 1)
    await measure_pulses(dut, cfg.failsafe_frames - 3)
    assert failsafe_active(dut) == 0, "failsafe asserted before keepalive command"

    await apply_uart_command(dut, cfg, "M")
    await measure_pulses(dut, cfg.failsafe_frames - 3)
    assert failsafe_active(dut) == 0, "keepalive command did not postpone timeout"

    await drive_to_failsafe(dut, cfg)
    assert failsafe_active(dut) == 1, "failsafe should eventually assert after keepalive interval expires"
