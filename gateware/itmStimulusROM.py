# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2023 1BitSquared <info@1bitsquared.com>
# SPDX-FileContributor: Written by Rachel Mant <git@dragonmux.network>
from torii import Elaboratable, Module, Signal, Shape, Memory
from torii.build import Platform

__all__ = (
	'ITMStimulusROM',
)

def itmStreamData():
	for char in range(ord('A'), ord('Z') + 1):
		yield char
	for char in range(ord('a'), ord('z') + 1):
		yield char
	for char in range(ord('0'), ord('9') + 1):
		yield char
	yield ord('\r')
	yield ord('\n')

class ITMStimulusROM(Elaboratable):
	def __init__(self):
		self.data = Signal(Shape(16, False))
		self.entry = Signal(range(64), reset = 0)

	def elaborate(self, _: Platform) -> Module:
		m = Module()

		# Create a new memory to store the ROM in
		m.submodules.rom = rom = Memory(width = 16, depth = 64)
		# Initialise the ROM with the ITM stream data
		rom.init = [(value << 8) | 0x01 for value in itmStreamData()]

		# Hook up the read side of the memory and make it available
		readPort = rom.read_port()
		m.d.comb += [
			readPort.addr.eq(self.entry),
			self.data.eq(readPort.data),
			readPort.en.eq(1),
		]

		return m
