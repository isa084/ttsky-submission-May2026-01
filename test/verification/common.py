from dataclasses import dataclass

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge

CLK_PERIOD_NS = 10
DEFAULT_SETTLE_CYCLES = 2
INVALID_COMMANDS = ("x", "?", "\n")
@dataclass(frozen=True)
class ServoTestConfig:
    clks_per_bit: int
    min_pulse_cycles: int
    center_pulse_cycles: int
    max_pulse_cycles: int
    failsafe_frames: int
    gate_level: bool


@dataclass(frozen=True)
class ActionObservation:
    previous_ack: int
    pulse_width: int | None


def register_test(module_globals, func):
    func.__qualname__ = func.__name__
    module_globals[func.__name__] = cocotb.test()(func)
    return module_globals[func.__name__]


def ack_bit(dut):
    return (dut.uo_out.value.to_unsigned() >> 1) & 0x1


def preset_code(dut):
    return (dut.uo_out.value.to_unsigned() >> 2) & 0xF


def servo_pwm(dut):
    return dut.uo_out.value.to_unsigned() & 0x1


def failsafe_active(dut):
    return (dut.uo_out.value.to_unsigned() >> 6) & 0x1


def sweep_active(dut):
    return (dut.uo_out.value.to_unsigned() >> 7) & 0x1


def cfg_value(dut, signal_name):
    return getattr(dut, signal_name).value.to_unsigned()


def read_test_config(dut):
    return ServoTestConfig(
        clks_per_bit=cfg_value(dut, "cfg_clks_per_bit"),
        min_pulse_cycles=cfg_value(dut, "cfg_min_pulse_cycles"),
        center_pulse_cycles=cfg_value(dut, "cfg_center_pulse_cycles"),
        max_pulse_cycles=cfg_value(dut, "cfg_max_pulse_cycles"),
        failsafe_frames=cfg_value(dut, "cfg_failsafe_frames"),
        gate_level=bool(cfg_value(dut, "cfg_gate_level")),
    )


def digit_pulse(cfg, digit):
    pulse_step = (cfg.max_pulse_cycles - cfg.min_pulse_cycles) // 9
    return cfg.min_pulse_cycles + (digit * pulse_step)


def set_uart_rx(dut, level):
    dut.ui_in.value = (dut.ui_in.value.to_unsigned() & 0xFE) | (level & 0x1)


def set_override_lines(dut, center=False, minimum=False, maximum=False):
    rx_idle = dut.ui_in.value.to_unsigned() & 0x1
    dut.ui_in.value = rx_idle | (int(center) << 1) | (int(minimum) << 2) | (int(maximum) << 3)


def clear_override_lines(dut):
    set_override_lines(dut, center=False, minimum=False, maximum=False)


def current_status(dut):
    return {
        "ack": ack_bit(dut),
        "preset": preset_code(dut),
        "failsafe": failsafe_active(dut),
        "sweep": sweep_active(dut),
    }


async def start_clock(dut):
    dut.clk.value = 0
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())
    await RisingEdge(dut.clk)


async def initialize_test(dut, test_name):
    dut._log.info("Start %s", test_name)

    await start_clock(dut)
    dut.ena.value = 1
    dut.uio_in.value = 0
    dut.ui_in.value = 0x01
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)

    cfg = read_test_config(dut)
    dut._log.info(
        "Config: clks_per_bit=%d min=%d center=%d max=%d failsafe_frames=%d gate_level=%d",
        cfg.clks_per_bit,
        cfg.min_pulse_cycles,
        cfg.center_pulse_cycles,
        cfg.max_pulse_cycles,
        cfg.failsafe_frames,
        cfg.gate_level,
    )
    return cfg


async def settle_control_path(dut, cycles=DEFAULT_SETTLE_CYCLES):
    await ClockCycles(dut.clk, cycles)


async def measure_next_pulse(dut):
    high_cycles = 0

    while servo_pwm(dut):
        await RisingEdge(dut.clk)

    while not servo_pwm(dut):
        await RisingEdge(dut.clk)

    while servo_pwm(dut):
        high_cycles += 1
        await RisingEdge(dut.clk)

    return high_cycles


async def measure_pulses(dut, count):
    pulse_widths = []
    for _ in range(count):
        pulse_widths.append(await measure_next_pulse(dut))
    return pulse_widths


async def send_uart_byte(dut, data, clks_per_bit):
    await FallingEdge(dut.clk)
    set_uart_rx(dut, 0)
    await ClockCycles(dut.clk, clks_per_bit)

    for bit_idx in range(8):
        await FallingEdge(dut.clk)
        set_uart_rx(dut, (data >> bit_idx) & 0x1)
        await ClockCycles(dut.clk, clks_per_bit)

    await FallingEdge(dut.clk)
    set_uart_rx(dut, 1)
    await ClockCycles(dut.clk, clks_per_bit * 2)


async def send_uart_command(dut, cfg, char):
    await send_uart_byte(dut, ord(char), cfg.clks_per_bit)


async def apply_uart_command(dut, cfg, char, *, measure_pulse=False):
    previous_ack = ack_bit(dut)
    await send_uart_command(dut, cfg, char)

    pulse_width = None
    if measure_pulse and not cfg.gate_level:
        pulse_width = await measure_next_pulse(dut)
    else:
        await settle_control_path(dut)

    return ActionObservation(previous_ack=previous_ack, pulse_width=pulse_width)


async def apply_override(dut, cfg, *, center=False, minimum=False, maximum=False, measure_pulse=False):
    previous_ack = ack_bit(dut)
    set_override_lines(dut, center=center, minimum=minimum, maximum=maximum)

    pulse_width = None
    if measure_pulse and not cfg.gate_level:
        pulse_width = await measure_next_pulse(dut)
    else:
        await settle_control_path(dut)

    return ActionObservation(previous_ack=previous_ack, pulse_width=pulse_width)


async def release_overrides(dut):
    clear_override_lines(dut)
    await settle_control_path(dut)


async def observe_reset_pulse(dut, cfg):
    if cfg.gate_level:
        await settle_control_path(dut)
        return None
    return await measure_next_pulse(dut)


async def drive_to_failsafe(dut, cfg):
    return await measure_pulses(dut, cfg.failsafe_frames + 2)
