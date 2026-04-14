import cocotb

from verification.common import (
    ack_bit,
    apply_override,
    apply_uart_command,
    digit_pulse,
    failsafe_active,
    initialize_test,
    measure_next_pulse,
    measure_pulses,
    preset_code,
    register_test,
    sweep_active,
)


def _make_sweep_enable_alias_test(char):
    async def _test(dut):
        cfg = await initialize_test(dut, f"Sweep enable alias {char!r}")
        previous_ack = ack_bit(dut)
        await apply_uart_command(dut, cfg, char)

        assert ack_bit(dut) != previous_ack, f"{char!r} did not toggle ack"
        assert sweep_active(dut) == 1, f"{char!r} did not enable sweep"
        assert failsafe_active(dut) == 0, f"{char!r} unexpectedly enabled failsafe"

    _test.__name__ = f"test_sweep_alias_{ord(char):02x}_enables_mode"
    return _test


for _char in ("s", "S"):
    register_test(globals(), _make_sweep_enable_alias_test(_char))


@cocotb.test()
async def test_sweep_advances_upward_from_center(dut):
    cfg = await initialize_test(dut, "Sweep advances from center")
    if cfg.gate_level:
        dut._log.info("Skipping sweep frame-step check in gate-level mode")
        return

    await apply_uart_command(dut, cfg, "s")
    first_sweep_width = await measure_next_pulse(dut)
    assert first_sweep_width == digit_pulse(cfg, 6), f"first sweep step produced {first_sweep_width}"
    assert preset_code(dut) == 6, f"first sweep step left preset code {preset_code(dut)}"


@cocotb.test()
async def test_sweep_advances_upward_from_minimum(dut):
    cfg = await initialize_test(dut, "Sweep advances from minimum")
    if cfg.gate_level:
        dut._log.info("Skipping sweep frame-step check in gate-level mode")
        return

    await apply_uart_command(dut, cfg, "m", measure_pulse=True)
    await apply_uart_command(dut, cfg, "s")
    first_sweep_width = await measure_next_pulse(dut)
    assert first_sweep_width == digit_pulse(cfg, 1), f"minimum-origin sweep produced {first_sweep_width}"
    assert preset_code(dut) == 1, f"minimum-origin sweep left preset code {preset_code(dut)}"


@cocotb.test()
async def test_sweep_reverses_from_maximum_endpoint(dut):
    cfg = await initialize_test(dut, "Sweep reverses from maximum")
    if cfg.gate_level:
        dut._log.info("Skipping sweep endpoint reversal in gate-level mode")
        return

    await apply_uart_command(dut, cfg, "M", measure_pulse=True)
    await apply_uart_command(dut, cfg, "s")
    first_sweep_width = await measure_next_pulse(dut)
    assert first_sweep_width == digit_pulse(cfg, 8), f"maximum-origin sweep produced {first_sweep_width}"
    assert preset_code(dut) == 8, f"maximum-origin sweep left preset code {preset_code(dut)}"


@cocotb.test()
async def test_sweep_changes_pulse_widths_over_multiple_frames(dut):
    cfg = await initialize_test(dut, "Sweep changes pulse widths")
    if cfg.gate_level:
        dut._log.info("Skipping sweep pulse-width progression in gate-level mode")
        return

    await apply_uart_command(dut, cfg, "s")
    sweep_widths = await measure_pulses(dut, 4)
    assert len(set(sweep_widths)) > 1, f"sweep did not change pulse widths: {sweep_widths}"
    assert failsafe_active(dut) == 0, "failsafe asserted during sweep"


@cocotb.test()
async def test_valid_uart_command_cancels_sweep_mode(dut):
    cfg = await initialize_test(dut, "Sweep canceled by UART command")
    await apply_uart_command(dut, cfg, "s")
    observation = await apply_uart_command(dut, cfg, "M", measure_pulse=not cfg.gate_level)

    assert sweep_active(dut) == 0, "UART command did not cancel sweep"
    assert preset_code(dut) == 9, f"maximum command after sweep left preset code {preset_code(dut)}"
    if observation.pulse_width is not None:
        assert observation.pulse_width == cfg.max_pulse_cycles, f"maximum command after sweep produced {observation.pulse_width}"


@cocotb.test()
async def test_override_cancels_sweep_mode(dut):
    cfg = await initialize_test(dut, "Sweep canceled by override")
    await apply_uart_command(dut, cfg, "s")
    await apply_override(dut, cfg, center=True, measure_pulse=not cfg.gate_level)

    assert sweep_active(dut) == 0, "override did not cancel sweep"
    assert preset_code(dut) == 5, f"center override after sweep left preset code {preset_code(dut)}"


@cocotb.test()
async def test_repeated_sweep_command_keeps_mode_active_and_toggles_ack(dut):
    cfg = await initialize_test(dut, "Repeated sweep command")
    previous_ack = ack_bit(dut)
    await apply_uart_command(dut, cfg, "s")
    mid_ack = ack_bit(dut)
    await apply_uart_command(dut, cfg, "S")

    assert mid_ack != previous_ack, "first sweep command did not toggle ack"
    assert ack_bit(dut) != mid_ack, "second sweep command did not toggle ack"
    assert sweep_active(dut) == 1, "repeated sweep command left mode inactive"


@cocotb.test()
async def test_sweep_activity_prevents_failsafe_timeout(dut):
    cfg = await initialize_test(dut, "Sweep prevents failsafe")
    if cfg.gate_level:
        dut._log.info("Skipping sweep timeout prevention test in gate-level mode")
        return

    await apply_uart_command(dut, cfg, "s")
    await measure_pulses(dut, cfg.failsafe_frames + 3)
    assert sweep_active(dut) == 1, "sweep should remain active during sweep timeout test"
    assert failsafe_active(dut) == 0, "failsafe should not assert while sweep is active"
