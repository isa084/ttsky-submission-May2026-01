import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge

CLK_PERIOD_NS = 10
SIM_CLKS_PER_BIT = 4


def ack_bit(dut):
    return (dut.uo_out.value.to_unsigned() >> 1) & 0x1


def preset_code(dut):
    return (dut.uo_out.value.to_unsigned() >> 2) & 0xF


def servo_pwm(dut):
    return dut.uo_out.value.to_unsigned() & 0x1


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


async def send_uart_byte(dut, data):
    await FallingEdge(dut.clk)
    set_uart_rx(dut, 0)
    await ClockCycles(dut.clk, SIM_CLKS_PER_BIT)

    for bit_idx in range(8):
        await FallingEdge(dut.clk)
        set_uart_rx(dut, (data >> bit_idx) & 0x1)
        await ClockCycles(dut.clk, SIM_CLKS_PER_BIT)

    await FallingEdge(dut.clk)
    set_uart_rx(dut, 1)
    await ClockCycles(dut.clk, SIM_CLKS_PER_BIT * 2)


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

    pulse_width = await measure_next_pulse(dut)
    assert pulse_width == 15, f"expected center pulse, got {pulse_width}"
    assert preset_code(dut) == 5, f"expected preset code 5 after reset, got {preset_code(dut)}"

    previous_ack = ack_bit(dut)
    await send_uart_byte(dut, ord("m"))
    pulse_width = await measure_next_pulse(dut)
    assert pulse_width == 10, f"expected min pulse, got {pulse_width}"
    assert preset_code(dut) == 0, f"expected preset code 0 after 'm', got {preset_code(dut)}"
    assert ack_bit(dut) != previous_ack, "ack bit did not toggle after 'm'"

    previous_ack = ack_bit(dut)
    await send_uart_byte(dut, ord("M"))
    pulse_width = await measure_next_pulse(dut)
    assert pulse_width == 19, f"expected max pulse, got {pulse_width}"
    assert preset_code(dut) == 9, f"expected preset code 9 after 'M', got {preset_code(dut)}"
    assert ack_bit(dut) != previous_ack, "ack bit did not toggle after 'M'"

    previous_ack = ack_bit(dut)
    await send_uart_byte(dut, ord("7"))
    pulse_width = await measure_next_pulse(dut)
    assert pulse_width == 17, f"expected digit 7 pulse, got {pulse_width}"
    assert preset_code(dut) == 7, f"expected preset code 7 after '7', got {preset_code(dut)}"
    assert ack_bit(dut) != previous_ack, "ack bit did not toggle after '7'"
    assert ((dut.uo_out.value.to_unsigned() >> 6) & 0x1) == 1, "command_seen flag was not set"

    previous_ack = ack_bit(dut)
    await send_uart_byte(dut, ord("x"))
    pulse_width = await measure_next_pulse(dut)
    assert pulse_width == 17, f"invalid command changed pulse width to {pulse_width}"
    assert ack_bit(dut) == previous_ack, "ack bit changed for invalid command"

    assert dut.uio_out.value.to_unsigned() == 0, f"expected uio_out tie-off, got {dut.uio_out.value.to_unsigned():#x}"
    assert dut.uio_oe.value.to_unsigned() == 0, f"expected uio_oe tie-off, got {dut.uio_oe.value.to_unsigned():#x}"
