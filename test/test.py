import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge

CLK_PERIOD_NS = 10


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


def digit_pulse(min_pulse_cycles, max_pulse_cycles, digit):
    pulse_step = (max_pulse_cycles - min_pulse_cycles) // 9
    return min_pulse_cycles + (digit * pulse_step)


def set_uart_rx(dut, level):
    dut.ui_in.value = (dut.ui_in.value.to_unsigned() & 0xFE) | (level & 0x1)


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


async def measure_pulses(dut, count):
    pulse_widths = []
    for _ in range(count):
        pulse_widths.append(await measure_next_pulse(dut))
    return pulse_widths


@cocotb.test()
async def test_project(dut):
    dut._log.info("Start UART servo test")

    dut.clk.value = 0
    dut.ena.value = 1
    dut.ui_in.value = 0x01
    dut.uio_in.value = 0
    dut.rst_n.value = 0

    clock = Clock(dut.clk, CLK_PERIOD_NS, unit="ns")
    cocotb.start_soon(clock.start())

    await ClockCycles(dut.clk, 2)
    dut.rst_n.value = 1

    clks_per_bit = cfg_value(dut, "cfg_clks_per_bit")
    min_pulse_cycles = cfg_value(dut, "cfg_min_pulse_cycles")
    center_pulse_cycles = cfg_value(dut, "cfg_center_pulse_cycles")
    max_pulse_cycles = cfg_value(dut, "cfg_max_pulse_cycles")
    failsafe_frames = cfg_value(dut, "cfg_failsafe_frames")
    gate_level = cfg_value(dut, "cfg_gate_level")
    digit_7_pulse_cycles = digit_pulse(min_pulse_cycles, max_pulse_cycles, 7)

    dut._log.info(
        "Test configuration: clks_per_bit=%d min=%d center=%d max=%d failsafe_frames=%d gate_level=%d",
        clks_per_bit,
        min_pulse_cycles,
        center_pulse_cycles,
        max_pulse_cycles,
        failsafe_frames,
        gate_level,
    )

    pulse_width = await measure_next_pulse(dut)
    assert pulse_width == center_pulse_cycles, f"expected center pulse, got {pulse_width}"
    assert preset_code(dut) == 5, f"expected preset code 5 after reset, got {preset_code(dut)}"
    assert failsafe_active(dut) == 0, "failsafe should be inactive after reset"
    assert sweep_active(dut) == 0, "sweep should be inactive after reset"

    previous_ack = ack_bit(dut)
    await send_uart_byte(dut, ord("m"), clks_per_bit)
    pulse_width = await measure_next_pulse(dut)
    assert pulse_width == min_pulse_cycles, f"expected min pulse, got {pulse_width}"
    assert preset_code(dut) == 0, f"expected preset code 0 after 'm', got {preset_code(dut)}"
    assert ack_bit(dut) != previous_ack, "ack bit did not toggle after 'm'"
    assert failsafe_active(dut) == 0, "failsafe should clear on valid command"
    assert sweep_active(dut) == 0, "sweep should stay inactive on preset commands"

    previous_ack = ack_bit(dut)
    await send_uart_byte(dut, ord("M"), clks_per_bit)
    pulse_width = await measure_next_pulse(dut)
    assert pulse_width == max_pulse_cycles, f"expected max pulse, got {pulse_width}"
    assert preset_code(dut) == 9, f"expected preset code 9 after 'M', got {preset_code(dut)}"
    assert ack_bit(dut) != previous_ack, "ack bit did not toggle after 'M'"
    assert failsafe_active(dut) == 0, "failsafe should remain inactive after 'M'"

    previous_ack = ack_bit(dut)
    await send_uart_byte(dut, ord("7"), clks_per_bit)
    pulse_width = await measure_next_pulse(dut)
    assert pulse_width == digit_7_pulse_cycles, f"expected digit 7 pulse, got {pulse_width}"
    assert preset_code(dut) == 7, f"expected preset code 7 after '7', got {preset_code(dut)}"
    assert ack_bit(dut) != previous_ack, "ack bit did not toggle after '7'"
    assert failsafe_active(dut) == 0, "failsafe should remain inactive after '7'"
    assert sweep_active(dut) == 0, "sweep should remain inactive after '7'"

    previous_ack = ack_bit(dut)
    await send_uart_byte(dut, ord("x"), clks_per_bit)
    pulse_width = await measure_next_pulse(dut)
    assert pulse_width == digit_7_pulse_cycles, f"invalid command changed pulse width to {pulse_width}"
    assert ack_bit(dut) == previous_ack, "ack bit changed for invalid command"

    previous_ack = ack_bit(dut)
    await send_uart_byte(dut, ord("s"), clks_per_bit)
    await ClockCycles(dut.clk, 2)
    assert ack_bit(dut) != previous_ack, "ack bit did not toggle after 's'"
    assert sweep_active(dut) == 1, "sweep mode did not enable"

    if not gate_level:
        sweep_widths = await measure_pulses(dut, 3)
        assert any(width > digit_7_pulse_cycles for width in sweep_widths), (
            f"sweep did not advance pulse widths: {sweep_widths}"
        )
        assert failsafe_active(dut) == 0, "failsafe unexpectedly asserted during sweep"

        previous_ack = ack_bit(dut)
        await send_uart_byte(dut, ord("M"), clks_per_bit)
        pulse_width = await measure_next_pulse(dut)
        assert pulse_width == max_pulse_cycles, f"expected max pulse before failsafe test, got {pulse_width}"
        assert ack_bit(dut) != previous_ack, "ack bit did not toggle before failsafe test"
        assert sweep_active(dut) == 0, "direct command should cancel sweep mode"

        timeout_widths = await measure_pulses(dut, failsafe_frames + 2)
        assert center_pulse_cycles in timeout_widths, (
            f"failsafe never returned pulse to center: {timeout_widths}"
        )
        assert failsafe_active(dut) == 1, "failsafe flag did not assert after inactivity"

    assert dut.uio_out.value.to_unsigned() == 0, f"expected uio_out tie-off, got {dut.uio_out.value.to_unsigned():#x}"
    assert dut.uio_oe.value.to_unsigned() == 0, f"expected uio_oe tie-off, got {dut.uio_oe.value.to_unsigned():#x}"
