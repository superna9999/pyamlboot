#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
# -*- coding: utf-8 -*-

#
# Command to chainload uboot using the "update" command from the stock
# Amlogic u-boot flashed on a device
#

from pyamlboot import pyamlboot
import sys

UBOOT_ADDR = 0x1000000

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: %s <u-boot.bin path>" % sys.argv[0])
        sys.exit(1)

    dev = pyamlboot.AmlogicSoC()

    print("Writing u-boot.bin...")
    with open(sys.argv[1], "rb") as f:
            b = f.read()
    dev.writeLargeMemory(UBOOT_ADDR, b, 512, True)

    print("Running go...")
    dev.tplCommand(1, "go 0x%x" % (UBOOT_ADDR))

