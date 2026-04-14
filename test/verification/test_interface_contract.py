import cocotb

from verification.common import initialize_test


@cocotb.test()
async def test_uio_out_is_tied_off(dut):
    await initialize_test(dut, "Output interface uio_out tie-off")
    assert dut.uio_out.value.to_unsigned() == 0, f"expected uio_out tie-off, got {dut.uio_out.value.to_unsigned():#x}"


@cocotb.test()
async def test_uio_oe_is_tied_off(dut):
    await initialize_test(dut, "Output interface uio_oe tie-off")
    assert dut.uio_oe.value.to_unsigned() == 0, f"expected uio_oe tie-off, got {dut.uio_oe.value.to_unsigned():#x}"
