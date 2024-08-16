# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2023 1BitSquared <info@1bitsquared.com>
# SPDX-FileContributor: Written by Rachel Mant <git@dragonmux.network>
from torii import Elaboratable, Module, Signal, Cat
from torii.build import Platform

__all__ = (
	'Button',
)

class Button(Elaboratable):
	def __init__(self) -> None:
		# Button input signal
		self.buttonIn = Signal()
		# Debounced button value out
		self.buttonValue = Signal()

	def elaborate(self, _: Platform):
		m = Module()

		# Input handling to get the button onto the sync domain
		buttonRaw = self.buttonIn
		buttonCurrent = Signal()
		m.d.sync += buttonCurrent.eq(buttonRaw)

		# Sampling trigger signal
		sampleTrigger = Signal()

		# Debounce register
		buttonDebounce = Signal(3, reset = 0)

		# Sampling counter
		sampleCounter = Signal(8)
		# When the top most bit of the counter becomes set, trigger sampling and reset the counter
		with m.If(sampleCounter[-1]):
			m.d.sync += sampleCounter.eq(0)
		with m.Else():
			m.d.sync += sampleCounter.eq(sampleCounter + 1)
		m.d.comb += sampleTrigger.eq(sampleCounter[-1])

		# Debounce handler
		with m.If(sampleTrigger):
			# Concatenate the current debounce state with the current synchronised button state
			# producing the bit vector [3:0] = {buttonDebounce, buttonCurrent}
			with m.Switch(Cat(buttonCurrent, buttonDebounce)):
				with m.Case('0--0'):
					m.d.sync += buttonDebounce.eq(0b000)
				with m.Case('0001'):
					m.d.sync += buttonDebounce.eq(0b001)
				with m.Case('0011'):
					m.d.sync += buttonDebounce.eq(0b010)
				with m.Case('0101'):
					m.d.sync += buttonDebounce.eq(0b011)
				with m.Case('0111', '1--1'):
					m.d.sync += buttonDebounce.eq(0b111)
				with m.Case('1110'):
					m.d.sync += buttonDebounce.eq(0b110)
				with m.Case('1100'):
					m.d.sync += buttonDebounce.eq(0b101)
				with m.Case('1010'):
					m.d.sync += buttonDebounce.eq(0b100)
				with m.Case('1000'):
					m.d.sync += buttonDebounce.eq(0b000)
				with m.Default():
					m.d.sync += buttonDebounce.eq(0b000)

		# Debounced button output
		m.d.comb += self.buttonValue.eq(buttonDebounce[-1])

		return m
