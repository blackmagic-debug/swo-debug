# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2023 1BitSquared <info@1bitsquared.com>
# SPDX-FileContributor: Written by Rachel Mant <git@dragonmux.network>
from torii.sim import Settle
from torii.test import ToriiTestCase
from ..manchester import ManchesterEncoder

class Platform:
	default_clk_frequency = 12e6

class ManchesterEncoderTestCase(ToriiTestCase):
	dut : ManchesterEncoder = ManchesterEncoder
	domains = (('sync', 12e6), )
	platform = Platform

	@ToriiTestCase.simulation
	@ToriiTestCase.sync_domain(domain = 'sync')
	def testEncoding(self):
		dut = self.dut
		halfBitPeriod = int(1 / (self.clk_period('sync') / 115200)) // 2
		# Check that things start up in a sensible state
		assert (yield dut.manchesterOut) == 0
		yield Settle()
		assert (yield dut.manchesterOut) == 0
		# Wait a little bit so we're misaligned to the internal bit clock
		yield from self.settle(15)
		# Signal we want to start talking
		yield dut.start.eq(1)
		yield
		yield dut.start.eq(0)
		yield from self.wait_until_high(dut.cycleComplete, timeout = halfBitPeriod * 3)
		# Now load on a 1-bit to check it encodes properly
		yield dut.bitIn.eq(1)
		yield
		yield from self.wait_until_high(dut.halfBitComplete, timeout = halfBitPeriod)
		# Check that the output is high right until the transition
		assert (yield dut.manchesterOut) == 1
		yield
		yield from self.wait_until_high(dut.cycleComplete, timeout = halfBitPeriod)
		# And then that the output is low at the end of the cycle
		assert (yield dut.manchesterOut) == 0
		# Now check a 0-bit for encoding
		yield dut.bitIn.eq(0)
		yield
		yield from self.wait_until_high(dut.halfBitComplete, timeout = halfBitPeriod)
		# Check that the output is low right until the transition
		assert (yield dut.manchesterOut) == 0
		# Tell the machinary that the next bit is a stop bit
		yield dut.stop.eq(1)
		yield
		yield dut.stop.eq(0)
		yield from self.wait_until_high(dut.cycleComplete, timeout = halfBitPeriod)
		# And then that the output is low at the end of the cycle
		assert (yield dut.manchesterOut) == 1
		yield
		# Now check that a stop bit is generated
		yield from self.wait_until_high(dut.halfBitComplete, timeout = halfBitPeriod)
		assert (yield dut.manchesterOut) == 0
		yield
		yield from self.wait_until_high(dut.cycleComplete, timeout = halfBitPeriod)
		assert (yield dut.manchesterOut) == 0
		yield
		# Check that things are properly idle now
		yield from self.wait_until_high(dut.halfBitComplete, timeout = halfBitPeriod)
		assert (yield dut.manchesterOut) == 0
		yield from self.step(50)
