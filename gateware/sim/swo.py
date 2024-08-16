# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2023 1BitSquared <info@1bitsquared.com>
# SPDX-FileContributor: Written by Rachel Mant <git@dragonmux.network>
from torii import Record
from torii.test import ToriiTestCase
from torii.hdl.rec import DIR_FANOUT, DIR_FANIN
from ..swo import SWO

swo = Record((
	('swo', [
		('o', 1, DIR_FANOUT),
	]),
	('trigger', [
		('i', 1, DIR_FANIN),
	]),
))

button = Record((
	('i', 1, DIR_FANIN),
))

led0 = Record((
	('o', 1, DIR_FANOUT),
))

led1 = Record((
	('o', 1, DIR_FANOUT),
))

class Platform:
	default_clk_frequency = 12e6

	def request(self, name, number):
		assert name in ('swo', 'button', 'led')
		if name == 'swo':
			assert number == 0
			return swo
		elif name == 'button':
			assert number == 0
			return button
		elif name == 'led':
			assert number == 0 or number == 1
			return led0 if number == 0 else led1

class SWOTestCase(ToriiTestCase):
	dut : SWO = SWO
	domains = (('sync', 12e6), )
	platform = Platform()

	@ToriiTestCase.simulation
	@ToriiTestCase.sync_domain(domain = 'sync')
	def testContinuous(self):
		halfBitPeriod = int((1 / self.clk_period('sync')) // 115200) // 2
		# Tell the gateware to switch into continuous mode
		assert (yield led1.o) == 0
		assert (yield swo.swo.o) == 0
		yield button.i.eq(1)
		yield from self.step((2**7) * 4)
		yield
		yield button.i.eq(0)
		yield from self.step(((2**7) * 4) + 6)
		# Check that continuous mode turns on
		assert (yield led1.o) == 0
		yield
		assert (yield led1.o) == 1
		yield
		# Now check that the SWO FSM starts running with SWO having been idle this whole time
		assert (yield swo.swo.o) == 0
		assert (yield led0.o) == 0
		yield
		assert (yield swo.swo.o) == 0
		assert (yield led0.o) == 1
		# Wait for the SWO clock to sync
		yield from self.step(5)
		# Check that we see a start bit
		assert (yield swo.swo.o) == 0
		yield
		assert (yield swo.swo.o) == 1
		yield from self.step(halfBitPeriod - 1)
		assert (yield swo.swo.o) == 0
		yield from self.step(halfBitPeriod - 2)
		assert (yield swo.swo.o) == 0
		yield
		# Now check the bits output by the encoder
		expectedData = 0x4101
		for shift in range(16):
			# Compute what we expect the output to be
			bit = (expectedData >> shift) & 1
			# Check that the encoder is presently outputting that
			assert (yield swo.swo.o) == bit
			# Now check that half a cycle later it transitions to the oposite
			yield from self.step(halfBitPeriod - 2)
			assert (yield swo.swo.o) == bit
			yield
			assert (yield swo.swo.o) == 1 - bit
			yield from self.step(halfBitPeriod - 2)
			assert (yield swo.swo.o) == 1 - bit
			yield
		# Now validate that the SWO encoder does a stop bit and goes back to idle (if briefly)
		assert (yield swo.swo.o) == 0
		yield from self.step(halfBitPeriod - 2)
		assert (yield swo.swo.o) == 0
		yield
		assert (yield swo.swo.o) == 0
		yield from self.step(halfBitPeriod - 3)
		assert (yield led0.o) == 1
		yield
		assert (yield swo.swo.o) == 0
		assert (yield led0.o) == 0
		yield
		assert (yield led0.o) == 0
		yield
		assert (yield swo.swo.o) == 0
		assert (yield led0.o) == 1
		# Check that it just keeps going
		yield from self.step((halfBitPeriod * 38) - 4)
		assert (yield led0.o) == 1
		yield
		assert (yield swo.swo.o) == 0
		assert (yield led0.o) == 0
		yield
		assert (yield led0.o) == 0
		yield
		assert (yield swo.swo.o) == 0
		assert (yield led0.o) == 1
