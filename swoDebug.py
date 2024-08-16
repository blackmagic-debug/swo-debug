#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2023 1BitSquared <info@1bitsquared.com>
# SPDX-FileContributor: Written by Rachel Mant <git@dragonmux.network>
from sys import argv, path, exit
from pathlib import Path

gatewarePath = Path(argv[0]).resolve().parent
if (gatewarePath / 'gateware').is_dir():
	path.insert(0, str(gatewarePath))
else:
	raise ImportError('Cannot find the SWO debug gateware')

from gateware import cli
if __name__ == '__main__':
	exit(cli())
