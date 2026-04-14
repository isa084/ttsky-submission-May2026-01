from verification.common import (
    INVALID_COMMANDS,
    ack_bit,
    apply_uart_command,
    digit_pulse,
    failsafe_active,
    initialize_test,
    preset_code,
    register_test,
    sweep_active,
)


def _make_digit_test(digit):
    async def _test(dut):
        cfg = await initialize_test(dut, f"UART digit {digit}")
        observation = await apply_uart_command(dut, cfg, str(digit), measure_pulse=not cfg.gate_level)

        assert preset_code(dut) == digit, f"digit {digit} left preset code {preset_code(dut)}"
        assert failsafe_active(dut) == 0, f"digit {digit} unexpectedly enabled failsafe"
        assert sweep_active(dut) == 0, f"digit {digit} unexpectedly enabled sweep"
        if observation.pulse_width is not None:
            assert observation.pulse_width == digit_pulse(cfg, digit), f"digit {digit} produced {observation.pulse_width}"

    _test.__name__ = f"test_uart_digit_{digit}_selects_expected_preset"
    return _test


for _digit in range(10):
    register_test(globals(), _make_digit_test(_digit))


def _make_named_position_test(char, expected_preset, description, pulse_reader):
    async def _test(dut):
        cfg = await initialize_test(dut, description)
        observation = await apply_uart_command(dut, cfg, char, measure_pulse=not cfg.gate_level)

        assert preset_code(dut) == expected_preset, f"{char!r} left preset code {preset_code(dut)}"
        assert failsafe_active(dut) == 0, f"{char!r} unexpectedly enabled failsafe"
        assert sweep_active(dut) == 0, f"{char!r} unexpectedly enabled sweep"
        if observation.pulse_width is not None:
            assert observation.pulse_width == pulse_reader(cfg), f"{char!r} produced {observation.pulse_width}"

    _test.__name__ = f"test_uart_command_{ord(char):02x}_updates_position"
    return _test


for _char, _preset, _description, _pulse_reader in (
    ("c", 5, "UART lowercase center command", lambda cfg: cfg.center_pulse_cycles),
    ("C", 5, "UART uppercase center command", lambda cfg: cfg.center_pulse_cycles),
    ("m", 0, "UART minimum command", lambda cfg: cfg.min_pulse_cycles),
    ("M", 9, "UART maximum command", lambda cfg: cfg.max_pulse_cycles),
):
    register_test(globals(), _make_named_position_test(_char, _preset, _description, _pulse_reader))


def _make_sweep_enable_test(char):
    async def _test(dut):
        cfg = await initialize_test(dut, f"UART sweep enable {char!r}")
        previous_ack = ack_bit(dut)
        await apply_uart_command(dut, cfg, char)

        assert ack_bit(dut) != previous_ack, f"{char!r} did not toggle ack"
        assert preset_code(dut) == 5, f"{char!r} changed preset code unexpectedly to {preset_code(dut)}"
        assert failsafe_active(dut) == 0, f"{char!r} unexpectedly enabled failsafe"
        assert sweep_active(dut) == 1, f"{char!r} did not enable sweep"

    _test.__name__ = f"test_uart_command_{ord(char):02x}_enables_sweep"
    return _test


for _char in ("s", "S"):
    register_test(globals(), _make_sweep_enable_test(_char))


def _make_invalid_command_test(char):
    async def _test(dut):
        cfg = await initialize_test(dut, f"UART invalid command {char!r}")
        previous_ack = ack_bit(dut)
        observation = await apply_uart_command(dut, cfg, char, measure_pulse=not cfg.gate_level)

        assert ack_bit(dut) == previous_ack, f"invalid command {char!r} toggled ack"
        assert preset_code(dut) == 5, f"invalid command {char!r} changed preset code to {preset_code(dut)}"
        assert failsafe_active(dut) == 0, f"invalid command {char!r} enabled failsafe"
        assert sweep_active(dut) == 0, f"invalid command {char!r} enabled sweep"
        if observation.pulse_width is not None:
            assert observation.pulse_width == cfg.center_pulse_cycles, f"invalid command {char!r} changed pulse"

    _test.__name__ = f"test_uart_invalid_command_{ord(char):02x}_is_ignored"
    return _test


for _char in INVALID_COMMANDS:
    register_test(globals(), _make_invalid_command_test(_char))


def _make_ack_toggle_test(char, description):
    async def _test(dut):
        cfg = await initialize_test(dut, description)
        previous_ack = ack_bit(dut)
        await apply_uart_command(dut, cfg, char)
        assert ack_bit(dut) != previous_ack, f"{char!r} did not toggle ack"

    _test.__name__ = f"test_uart_command_{ord(char):02x}_toggles_ack"
    return _test


for _char, _description in (
    ("4", "UART digit acknowledge toggle"),
    ("c", "UART center acknowledge toggle"),
    ("m", "UART minimum acknowledge toggle"),
    ("M", "UART maximum acknowledge toggle"),
    ("s", "UART sweep acknowledge toggle"),
):
    register_test(globals(), _make_ack_toggle_test(_char, _description))
