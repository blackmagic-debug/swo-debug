# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2023 1BitSquared <info@1bitsquared.com>
# SPDX-FileContributor: Written by Rachel Mant <git@dragonmux.network>
from subprocess import CalledProcessError
from torii.build import Resource, Subsignal, Pins, Attrs
from torii_boards.lattice.icebreaker import ICEBreakerPlatform
from .swo import SWO

__all__ = (
	'cli',
)

def cli():
	from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
	import logging

	# Configure basic logging so it's ready to go from right at the start
	configureLogging()

	# Build the command line parser
	parser = ArgumentParser(formatter_class = ArgumentDefaultsHelpFormatter,
		description = 'Black Magic Probe Manchester-coded SWO debugger')
	parser.add_argument('--verbose', '-v', action = 'store_true', help = 'Enable debugging output')

	actions = parser.add_subparsers(dest = 'action', required = True)
	buildAction = actions.add_parser('build', help = 'Build the SWO debug gateware')
	actions.add_parser('sim', help = 'Simulate and test the gateware components')

	# Allow the user to pick a seed if their toolchain is not giving good nextpnr runs
	buildAction.add_argument('--seed', action = 'store', type = int, default = 0,
		help = 'The nextpnr seed to use for the gateware build (default 0)')

	# Parse the command line and, if `-v` is specified, bump up the logging level
	args = parser.parse_args()
	if args.verbose:
		from logging import root, DEBUG
		root.setLevel(DEBUG)

	# Dispatch the action requested
	if args.action == 'sim':
		from unittest.loader import TestLoader
		from unittest.runner import TextTestRunner

		loader = TestLoader()
		tests = loader.discover(start_dir = 'gateware.sim', pattern = '*.py')

		runner = TextTestRunner()
		runner.run(tests)
		return 0
	elif args.action == 'build':
		platform = ICEBreakerPlatform()
		platform.add_resources([
			Resource('swo', 0,
				Subsignal('swo', Pins('46', dir = 'o'), Attrs(IO_STANDARD = 'SB_LVCMOS')),
				Subsignal('trigger', Pins('44', dir = 'i'), Attrs(IO_STANDARD = 'SB_LVCMOS')),
			)
		])
		try:
			nextpnrOptions = ['--tmg-ripup', f'--seed={args.seed}', '--write', 'swoDebug.pnr.json']
			platform.build(SWO(), name = 'swoDebug', synth_opts = '-abc9', nextpnr_opts = nextpnrOptions)
		except CalledProcessError:
			logging.error('Synthesising gateware and building bitstream failed, see build logs for details')
			return 1
		return 0

	logging.error("Unknown action requested")
	return 2

def configureLogging():
	from rich.logging import RichHandler
	import logging

	logging.basicConfig(
		force = True,
		format = '%(message)s',
		level = logging.INFO,
		handlers = [RichHandler(rich_tracebacks = True, show_path = False)]
	)
