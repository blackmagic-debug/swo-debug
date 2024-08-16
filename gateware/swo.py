# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2023 1BitSquared <info@1bitsquared.com>
# SPDX-FileContributor: Written by Rachel Mant <git@dragonmux.network>
from torii import Elaboratable, Module, Signal, Const, EnableInserter, Shape
from torii.build import Platform
from enum import IntEnum, unique
from .manchester import ManchesterEncoder
from .button import Button

__all__ = (
	'SWO',
)

@unique
class SWOMode(IntEnum):
	triggered = 0
	continuous = 1

class SWO(Elaboratable):
	def elaborate(self, platform: Platform) -> Module:
		m = Module()
		# Start by grabbing the SWO interface to use for I/O
		interface = platform.request('swo', 0)

		# Unpack the trigger and SWO pins/signals
		trigger: Signal = interface.trigger.i
		# SWO output is on the second to last
		swo: Signal = interface.swo.o

		# Grab the two LEDs to indicate state machine mode and activity with
		ledRun = platform.request('led', 0).o
		ledState = platform.request('led', 1).o

		# 0x01 0x41 ('A' on ITM channel 0)
		data = Const(0x4101, Shape(16, False))
		bit = Signal(range(17), reset = 0)
		mode = Signal(SWOMode, reset = SWOMode.triggered)

		encoderEnable = Signal()
		outputDelayed = Signal()
		outputRising = Signal()
		running = Signal()
		idle = Signal()

		# Instance the Manchester encoder block behind a clock gate so we can halt it on each rising edge
		# on the output SWO signal for triggered mode
		encoder: ManchesterEncoder = EnableInserter({'sync': encoderEnable})(ManchesterEncoder())
		m.submodules.encoder = encoder

		# Delay the output a cycle
		m.d.sync += outputDelayed.eq(encoder.manchesterOut)
		# And generate a pulse signal when the rising edge condition is detected
		m.d.comb += outputRising.eq(~outputDelayed & encoder.manchesterOut)

		# Start the state machine by going into an idle state and waiting for either a mode change or trigger signal
		with m.FSM(name = 'swo') as fsm:
			# Pull out the idle and running states
			m.d.comb += idle.eq(fsm.ongoing('IDLE') | fsm.ongoing('START'))
			m.d.comb += running.eq(fsm.ongoing('TRANSMIT') | fsm.ongoing('STOP'))
			stopping = fsm.ongoing('STOP')

			with m.State('IDLE'):
				with m.If(trigger | (mode == SWOMode.continuous)):
					m.next = 'START'
			with m.State('START'):
				m.d.comb += encoder.start.eq(1)
				m.next = 'TRANSMIT'
			with m.State('TRANSMIT'):
				# When the previous bit completes
				with m.If(encoder.cycleComplete):
					# Queue the next, if there are more to go
					with m.If(bit != 16):
						m.d.comb += encoder.bitIn.eq(data.bit_select(bit, 1))
						m.d.sync += bit.eq(bit + 1)
					# Otherwise, do a stop bit
					with m.Else():
						m.d.comb += encoder.stop.eq(1)
						m.d.sync += bit.eq(0)
						m.next = 'STOP'
			with m.State('STOP'):
				# Wait for the stop bit to finish
				with m.If(encoder.cycleComplete):
					# Go back to IDLE now we're done
					m.next = 'IDLE'

		# Enable the clock to the encoder when it is either a) idle, or b) running and we get re-triggered
		# Disable the clock when, while running, we see a rising edge on the output
		with m.If(idle | (mode == SWOMode.continuous)):
			m.d.sync += encoderEnable.eq(1)
		with m.Elif(running & outputRising):
			m.d.sync += encoderEnable.eq(0)
		with m.Elif(running & trigger):
			m.d.sync += encoderEnable.eq(1)

		# Instance the button handling block to get a stable button state signal out
		m.submodules.modeButton = modeButton = Button()
		# Plumb the block up to feed in the button and get its state out
		modeButtonValue = Signal()
		m.d.comb += [
			modeButton.buttonIn.eq(platform.request('button', 0).i),
			modeButtonValue.eq(modeButton.buttonValue),
		]

		# Registers for determining the falling edge of the button and generating a mode change from it
		modeButtonDelayed = Signal()
		m.d.sync += modeButtonDelayed.eq(modeButtonValue)
		modeSwitchTrigger = Signal()
		m.d.comb += modeSwitchTrigger.eq(modeButtonDelayed & ~modeButtonValue)
		modeSwitchPending = Signal()
		modeSwitchDone = Signal()
		m.d.comb += modeSwitchDone.eq(0)

		# When the mode button trigger is met, switch modes
		with m.If(modeSwitchTrigger):
			m.d.sync += modeSwitchPending.eq(1)
		with m.Elif(modeSwitchDone):
			m.d.sync += modeSwitchPending.eq(0)

		with m.If(modeSwitchPending):
			with m.If(mode == SWOMode.triggered):
				m.d.sync += mode.eq(SWOMode.continuous)
				m.d.comb += modeSwitchDone.eq(1)
			with m.Elif((mode == SWOMode.continuous) & stopping):
				m.d.sync += mode.eq(SWOMode.triggered)
				m.d.comb += modeSwitchDone.eq(1)

		m.d.comb += [
			# Plumb the Manchester-encoded SWO signal to the output pin
			swo.eq(encoder.manchesterOut),
			# Provide the current operating mode on the green LED
			ledState.eq(mode == SWOMode.continuous),
			# And indicate when the SWO output is active using the red
			ledRun.eq(running & encoderEnable)
		]
		return m
