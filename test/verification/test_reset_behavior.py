from verification.common import (
    ack_bit,
    failsafe_active,
    initialize_test,
    observe_reset_pulse,
    preset_code,
    register_test,
    servo_pwm,
    sweep_active,
)


def _make_reset_flag_test(name, label, reader, expected):
    async def _test(dut):
        cfg = await initialize_test(dut, label)
        pulse_width = await observe_reset_pulse(dut, cfg)

        if pulse_width is not None:
            assert pulse_width == cfg.center_pulse_cycles, f"reset pulse width was {pulse_width}"
        assert reader(dut) == expected, f"{label} expected {expected}, got {reader(dut)}"

    _test.__name__ = name
    return _test


register_test(
    globals(),
    _make_reset_flag_test(
        "test_reset_starts_at_center_preset",
        "Reset preset code",
        preset_code,
        5,
    ),
)
register_test(
    globals(),
    _make_reset_flag_test(
        "test_reset_clears_ack_toggle",
        "Reset acknowledge state",
        ack_bit,
        0,
    ),
)
register_test(
    globals(),
    _make_reset_flag_test(
        "test_reset_clears_failsafe_flag",
        "Reset failsafe flag",
        failsafe_active,
        0,
    ),
)
register_test(
    globals(),
    _make_reset_flag_test(
        "test_reset_clears_sweep_flag",
        "Reset sweep flag",
        sweep_active,
        0,
    ),
)


async def test_reset_drives_pwm_high_at_frame_start(dut):
    await initialize_test(dut, "Reset PWM level")
    assert servo_pwm(dut) == 1, f"reset left PWM low at frame start: {servo_pwm(dut)}"


test_reset_drives_pwm_high_at_frame_start = register_test(globals(), test_reset_drives_pwm_high_at_frame_start)
