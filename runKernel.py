#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# Command to run a kernel using the "update" command from the stock
# Amlogic u-boot flashed on a device
#

from pyamlboot import pyamlboot
import sys

UBOOT_IMAGEADDR = 0x8080000
UBOOT_DTBADDR = 0x8008000
UBOOT_INITRDADDR = 0x13000000

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: %s <uImage path> <dtb path> <rootfs path> \"<cmdline>\"" % sys.argv[0])
        sys.exit(1)

    dev = pyamlboot.AmlogicSoC()

    print("Writing uImage...")
    with open(sys.argv[1], "rb") as f:
            b = f.read()
    dev.writeLargeMemory(UBOOT_IMAGEADDR, b, 512, True)

    print("Writing dtb...")
    with open(sys.argv[2], "rb") as f:
            b = f.read()
    dev.writeLargeMemory(UBOOT_DTBADDR, b, 512, True)

    if sys.argv[3] != "-":
	    print("Writing rootfs...")
	    with open(sys.argv[3], "rb") as f:
		    b = f.read()
	    dev.writeLargeMemory(UBOOT_INITRDADDR, b, 512, True)

    print("Running bootm...")
    if sys.argv[3] != "-":
        dev.tplCommand(1, "setenv bootargs %s ; bootm 0x%x 0x%x 0x%x" % (sys.argv[4], UBOOT_IMAGEADDR, UBOOT_INITRDADDR, UBOOT_DTBADDR))
    else:
        dev.tplCommand(1, "setenv bootargs %s ; bootm 0x%x - 0x%x" % (sys.argv[4], UBOOT_IMAGEADDR, UBOOT_DTBADDR))

