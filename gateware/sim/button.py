# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2023 1BitSquared <info@1bitsquared.com>
# SPDX-FileContributor: Written by Rachel Mant <git@dragonmux.network>
from torii.test import ToriiTestCase
from ..button import Button

class ButtonTestCase(ToriiTestCase):
	dut : Button = Button
	domains = (('sync', 12e6), )

	@ToriiTestCase.simulation
	@ToriiTestCase.sync_domain(domain = 'sync')
	def testDebouncing(self):
		dut = self.dut
		# Set the input up and run till the first sampling point
		yield dut.buttonIn.eq(0)
		assert (yield dut.buttonValue) == 0
		yield from self.step((2**7) - 3)
		# Check that the output is still low and now load up the input with the button becomming pressed
		yield dut.buttonIn.eq(1)
		yield
		assert (yield dut.buttonValue) == 0
		yield
		assert (yield dut.buttonValue) == 0
		# For each of the next 3 sample cycles, we should see the output stay low
		for _ in range(3):
			yield from self.step((2**7))
			assert (yield dut.buttonValue) == 0
		# Then on the 4th it should go high
		yield
		assert (yield dut.buttonValue) == 1
		# Now wiggle the input (it should remain high)
		yield from self.step((2**6) - 1)
		yield dut.buttonIn.eq(0)
		yield from self.step((2**6) - 1)
		assert (yield dut.buttonValue) == 1
		yield from self.step((2**6) - 1)
		yield dut.buttonIn.eq(1)
		yield from self.step((2**6) - 1)
		assert (yield dut.buttonValue) == 1
		# Now let the input go and stay low and validate that it goes back to idle correctly
		yield dut.buttonIn.eq(0)
		yield
		assert (yield dut.buttonValue) == 1
		for _ in range(4):
			yield from self.step((2**7))
			assert (yield dut.buttonValue) == 1
		yield
		assert (yield dut.buttonValue) == 0
		# Finally, wiggle the input (it should remain low)
		yield from self.step((2**6) - 1)
		yield dut.buttonIn.eq(1)
		yield from self.step((2**6) - 1)
		assert (yield dut.buttonValue) == 0
		yield from self.step((2**6) - 1)
		yield dut.buttonIn.eq(0)
		yield from self.step((2**6) - 1)
		assert (yield dut.buttonValue) == 0
		yield
		assert (yield dut.buttonValue) == 0
