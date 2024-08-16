# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2023 1BitSquared <info@1bitsquared.com>
# SPDX-FileContributor: Written by Rachel Mant <git@dragonmux.network>
from torii import Elaboratable, Module, Signal
from torii.build import Platform

__all__ = (
	'ManchesterEncoder',
)

class ManchesterEncoder(Elaboratable):
	def __init__(self) -> None:
		# Data bit to encode
		self.bitIn = Signal()
		# Manchester coded data stream out
		self.manchesterOut = Signal()

		# Condition signals
		self.start = Signal()
		self.stop = Signal()
		# Cycle completion signal
		self.cycleComplete = Signal()
		# Half bit period completion signal
		self.halfBitComplete = Signal()

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		# Set up a counter to encode data at 115200 baud
		bitPeriod = int(platform.default_clk_frequency // 115200)
		halfBitPeriod = bitPeriod // 2
		halfBitPeriodCounter = Signal(range(halfBitPeriod), reset = 0)

		# Decode when a timing step should be taken
		step = halfBitPeriodCounter == 0
		# Describe an up counter bounded on the half bit period to generate the manchester encoder timings
		with m.If(halfBitPeriodCounter == halfBitPeriod - 1):
			m.d.sync += halfBitPeriodCounter.eq(0)
		with m.Else():
			m.d.sync += halfBitPeriodCounter.eq(halfBitPeriodCounter + 1)

		# Generate a clock signal based on the timer
		clock = Signal()
		with m.If(step):
			m.d.sync += clock.eq(~clock)
		m.d.comb += self.halfBitComplete.eq(step)
		cycleComplete = Signal()
		delayedClock = Signal()
		m.d.sync += [
			cycleComplete.eq(step & ~clock),
			delayedClock.eq(clock),
		]

		# Default state for the output is to be low
		m.d.comb += self.manchesterOut.eq(0)

		# Internal signal for holding the data bit to output
		data = Signal()
		with m.If(cycleComplete):
			m.d.sync += data.eq(self.bitIn)

		# Internal signal for holding if a stop has been requested since the last start of bit cycle
		stopPending = Signal()
		with m.If(self.stop):
			m.d.sync += stopPending.eq(1)
		with m.Elif(cycleComplete):
			m.d.sync += stopPending.eq(0)

		# NB, the clock described above is free-running, so encoding must be too
		with m.FSM(name = 'manchester') as fsm:
			# Output cycle completions for all states that aren't IDLE and WAIT_START
			m.d.comb += self.cycleComplete.eq(step & ~clock & ~(fsm.ongoing('IDLE') | fsm.ongoing('WAIT_START')))

			with m.State('IDLE'):
				# Having been asked to start encoding, wait for the clock to go to the right state
				with m.If(self.start):
					m.next = 'WAIT_START'
			with m.State('WAIT_START'):
				# Once we see the clock about to go through a rising edge, start the start bit sequence
				with m.If(cycleComplete):
					m.next = 'START_BIT'
			with m.State('START_BIT'):
				# Start bit is just the clock put on the line
				m.d.comb += self.manchesterOut.eq(delayedClock)
				# Wait for the completion of the cycle and as the next rising edge would happen, switch to bit encoding
				with m.If(cycleComplete):
					m.next = 'BIT_ENCODE'
			with m.State('BIT_ENCODE'):
				# The output bit is the clock xnor'd with the input bit
				m.d.comb += self.manchesterOut.eq(~(data ^ delayedClock))
				# Wait for the completion of the cycle to check if we should change states at all
				with m.If(cycleComplete):
					with m.If(stopPending):
						m.next = 'STOP_BIT'
			with m.State('STOP_BIT'):
				# Wait for a full bit cycle to re-enter idle to guarantee two half bit periods of low
				with m.If(cycleComplete):
					m.next = 'IDLE'

		return m
