import cocotb

from verification.common import (
    ack_bit,
    apply_override,
    apply_uart_command,
    drive_to_failsafe,
    failsafe_active,
    initialize_test,
    preset_code,
    register_test,
    release_overrides,
    sweep_active,
)


def _make_single_override_test(name, description, expected_preset, expected_pulse, *, center=False, minimum=False, maximum=False):
    async def _test(dut):
        cfg = await initialize_test(dut, description)
        observation = await apply_override(
            dut,
            cfg,
            center=center,
            minimum=minimum,
            maximum=maximum,
            measure_pulse=not cfg.gate_level,
        )

        assert preset_code(dut) == expected_preset, f"{description} left preset code {preset_code(dut)}"
        assert failsafe_active(dut) == 0, f"{description} unexpectedly enabled failsafe"
        assert sweep_active(dut) == 0, f"{description} unexpectedly enabled sweep"
        if observation.pulse_width is not None:
            assert observation.pulse_width == expected_pulse(cfg), f"{description} produced {observation.pulse_width}"

    _test.__name__ = name
    return _test


register_test(
    globals(),
    _make_single_override_test(
        "test_override_center_selects_center_preset",
        "Override center selection",
        5,
        lambda cfg: cfg.center_pulse_cycles,
        center=True,
    ),
)
register_test(
    globals(),
    _make_single_override_test(
        "test_override_minimum_selects_min_preset",
        "Override minimum selection",
        0,
        lambda cfg: cfg.min_pulse_cycles,
        minimum=True,
    ),
)
register_test(
    globals(),
    _make_single_override_test(
        "test_override_maximum_selects_max_preset",
        "Override maximum selection",
        9,
        lambda cfg: cfg.max_pulse_cycles,
        maximum=True,
    ),
)


def _make_override_priority_test(name, description, expected_preset, expected_pulse, *, center=False, minimum=False, maximum=False):
    async def _test(dut):
        cfg = await initialize_test(dut, description)
        observation = await apply_override(
            dut,
            cfg,
            center=center,
            minimum=minimum,
            maximum=maximum,
            measure_pulse=not cfg.gate_level,
        )

        assert preset_code(dut) == expected_preset, f"{description} produced preset {preset_code(dut)}"
        if observation.pulse_width is not None:
            assert observation.pulse_width == expected_pulse(cfg), f"{description} produced {observation.pulse_width}"

    _test.__name__ = name
    return _test


register_test(
    globals(),
    _make_override_priority_test(
        "test_override_center_has_priority_over_minimum",
        "Override priority center over minimum",
        5,
        lambda cfg: cfg.center_pulse_cycles,
        center=True,
        minimum=True,
    ),
)
register_test(
    globals(),
    _make_override_priority_test(
        "test_override_center_has_priority_over_maximum",
        "Override priority center over maximum",
        5,
        lambda cfg: cfg.center_pulse_cycles,
        center=True,
        maximum=True,
    ),
)
register_test(
    globals(),
    _make_override_priority_test(
        "test_override_minimum_has_priority_over_maximum",
        "Override priority minimum over maximum",
        0,
        lambda cfg: cfg.min_pulse_cycles,
        minimum=True,
        maximum=True,
    ),
)


@cocotb.test()
async def test_override_release_holds_last_forced_target(dut):
    cfg = await initialize_test(dut, "Override release holds forced target")
    observation = await apply_override(dut, cfg, minimum=True, measure_pulse=not cfg.gate_level)
    assert preset_code(dut) == 0, f"minimum override produced preset {preset_code(dut)}"
    if observation.pulse_width is not None:
        assert observation.pulse_width == cfg.min_pulse_cycles, f"minimum override produced {observation.pulse_width}"

    await release_overrides(dut)
    assert preset_code(dut) == 0, f"releasing override changed preset code to {preset_code(dut)}"


@cocotb.test()
async def test_override_does_not_toggle_ack(dut):
    cfg = await initialize_test(dut, "Override acknowledge isolation")
    previous_ack = ack_bit(dut)
    await apply_override(dut, cfg, center=True)
    assert ack_bit(dut) == previous_ack, "override changed acknowledge bit"


@cocotb.test()
async def test_override_clears_active_sweep_mode(dut):
    cfg = await initialize_test(dut, "Override clears sweep")
    await apply_uart_command(dut, cfg, "s")
    assert sweep_active(dut) == 1, "sweep did not start"

    await apply_override(dut, cfg, maximum=True)
    assert sweep_active(dut) == 0, "override did not clear sweep"
    assert preset_code(dut) == 9, f"override after sweep produced preset {preset_code(dut)}"


@cocotb.test()
async def test_override_clears_failsafe_state(dut):
    cfg = await initialize_test(dut, "Override clears failsafe")
    if cfg.gate_level:
        dut._log.info("Skipping failsafe-clear override test in gate-level mode")
        return

    await apply_uart_command(dut, cfg, "M", measure_pulse=True)
    await drive_to_failsafe(dut, cfg)
    assert failsafe_active(dut) == 1, "failsafe did not assert"

    await apply_override(dut, cfg, center=True, measure_pulse=True)
    assert failsafe_active(dut) == 0, "center override did not clear failsafe"
    assert preset_code(dut) == 5, f"center override left preset code {preset_code(dut)}"
