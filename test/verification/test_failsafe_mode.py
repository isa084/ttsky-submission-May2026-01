import cocotb

from verification.common import (
    INVALID_COMMANDS,
    apply_override,
    apply_uart_command,
    digit_pulse,
    drive_to_failsafe,
    failsafe_active,
    initialize_test,
    measure_pulses,
    preset_code,
    register_test,
    sweep_active,
)


def _make_failsafe_entry_test(name, description, start_command):
    async def _test(dut):
        cfg = await initialize_test(dut, description)
        if cfg.gate_level:
            dut._log.info("Skipping failsafe timeout entry test in gate-level mode")
            return

        await apply_uart_command(dut, cfg, start_command, measure_pulse=True)
        timeout_widths = await drive_to_failsafe(dut, cfg)

        assert cfg.center_pulse_cycles in timeout_widths, f"{description} never returned to center: {timeout_widths}"
        assert failsafe_active(dut) == 1, f"{description} did not assert failsafe"
        assert preset_code(dut) == 5, f"{description} left preset code {preset_code(dut)}"
        assert sweep_active(dut) == 0, f"{description} left sweep active"

    _test.__name__ = name
    return _test


register_test(
    globals(),
    _make_failsafe_entry_test(
        "test_failsafe_timeout_from_maximum_returns_to_center",
        "Failsafe timeout from maximum",
        "M",
    ),
)
register_test(
    globals(),
    _make_failsafe_entry_test(
        "test_failsafe_timeout_from_minimum_returns_to_center",
        "Failsafe timeout from minimum",
        "m",
    ),
)
register_test(
    globals(),
    _make_failsafe_entry_test(
        "test_failsafe_timeout_from_digit_returns_to_center",
        "Failsafe timeout from digit 7",
        "7",
    ),
)


@cocotb.test()
async def test_failsafe_flag_asserts_only_after_timeout_threshold(dut):
    cfg = await initialize_test(dut, "Failsafe threshold timing")
    if cfg.gate_level:
        dut._log.info("Skipping failsafe threshold timing test in gate-level mode")
        return

    await apply_uart_command(dut, cfg, "M", measure_pulse=True)
    await measure_pulses(dut, cfg.failsafe_frames - 2)
    assert failsafe_active(dut) == 0, "failsafe asserted before timeout threshold"

    await measure_pulses(dut, 2)
    assert failsafe_active(dut) == 1, "failsafe did not assert after timeout threshold"


@cocotb.test()
async def test_valid_uart_command_clears_failsafe_state(dut):
    cfg = await initialize_test(dut, "Failsafe cleared by valid UART command")
    if cfg.gate_level:
        dut._log.info("Skipping failsafe clear test in gate-level mode")
        return

    await apply_uart_command(dut, cfg, "M", measure_pulse=True)
    await drive_to_failsafe(dut, cfg)
    observation = await apply_uart_command(dut, cfg, "2", measure_pulse=True)

    assert failsafe_active(dut) == 0, "digit command did not clear failsafe"
    assert preset_code(dut) == 2, f"digit command left preset code {preset_code(dut)}"
    assert observation.pulse_width == digit_pulse(cfg, 2), f"digit 2 produced {observation.pulse_width}"


@cocotb.test()
async def test_override_clears_failsafe_state(dut):
    cfg = await initialize_test(dut, "Failsafe cleared by override")
    if cfg.gate_level:
        dut._log.info("Skipping failsafe clear test in gate-level mode")
        return

    await apply_uart_command(dut, cfg, "M", measure_pulse=True)
    await drive_to_failsafe(dut, cfg)
    await apply_override(dut, cfg, minimum=True, measure_pulse=True)

    assert failsafe_active(dut) == 0, "minimum override did not clear failsafe"
    assert preset_code(dut) == 0, f"minimum override left preset code {preset_code(dut)}"


@cocotb.test()
async def test_invalid_command_does_not_clear_failsafe_state(dut):
    cfg = await initialize_test(dut, "Failsafe survives invalid command")
    if cfg.gate_level:
        dut._log.info("Skipping invalid-command failsafe test in gate-level mode")
        return

    await apply_uart_command(dut, cfg, "M", measure_pulse=True)
    await drive_to_failsafe(dut, cfg)
    await apply_uart_command(dut, cfg, INVALID_COMMANDS[0], measure_pulse=True)

    assert failsafe_active(dut) == 1, "invalid command cleared failsafe"
    assert preset_code(dut) == 5, f"invalid command changed preset code to {preset_code(dut)}"


@cocotb.test()
async def test_valid_command_resets_inactivity_counter(dut):
    cfg = await initialize_test(dut, "Failsafe counter reset by valid UART")
    if cfg.gate_level:
        dut._log.info("Skipping inactivity counter reset test in gate-level mode")
        return

    await apply_uart_command(dut, cfg, "M", measure_pulse=True)
    await measure_pulses(dut, cfg.failsafe_frames - 3)
    assert failsafe_active(dut) == 0, "failsafe asserted too early"

    await apply_uart_command(dut, cfg, "m", measure_pulse=True)
    await measure_pulses(dut, cfg.failsafe_frames - 3)
    assert failsafe_active(dut) == 0, "keepalive UART command did not reset inactivity counter"


@cocotb.test()
async def test_override_resets_inactivity_counter(dut):
    cfg = await initialize_test(dut, "Failsafe counter reset by override")
    if cfg.gate_level:
        dut._log.info("Skipping inactivity counter reset test in gate-level mode")
        return

    await apply_uart_command(dut, cfg, "M", measure_pulse=True)
    await measure_pulses(dut, cfg.failsafe_frames - 3)
    await apply_override(dut, cfg, center=True, measure_pulse=True)
    await measure_pulses(dut, cfg.failsafe_frames - 3)
    assert failsafe_active(dut) == 0, "override did not reset inactivity counter"
