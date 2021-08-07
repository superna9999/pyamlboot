#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# Command to run a kernel using the "update" command from the stock
# Amlogic u-boot flashed on a device
#

import argparse

from pyamlboot import pyamlboot

UBOOT_IMAGEADDR = 0x8080000
UBOOT_DTBADDR = 0x8008000
UBOOT_INITRDADDR = 0x13000000

if __name__ == '__main__':
    def FileNoStdin(arg):
        if arg == "-":
            return None
        else:
            return argparse.FileType('rb')(arg)

    parser = argparse.ArgumentParser(
        description="Boot a kernel via Amlogic U-Boot's USB loader mode.")
    parser.add_argument(
        "kernel", type=FileNoStdin,
        help="kernel image to boot as uImage or Image/zImage, depending on -p")
    parser.add_argument(
        "dtb", type=FileNoStdin,
        help="device tree blob to pass to kernel")
    parser.add_argument(
        "ramdisk", type=FileNoStdin, nargs='?',
        help="ramdisk to pass to the kernel")
    parser.add_argument(
        "cmdline", nargs='?', default="",
        help="command line arguments to pass to the kernel")
    parser.add_argument(
        "-p", "--plain-image", action="store_true",
        help="expect a Image/zImage instead of a uImage (which is the default)")
    parser.add_argument(
        "-n", "--no-escape", action="store_true",
        help="don't shell-escape the command line when sending it to U-Boot")

    args = parser.parse_args()

    dev = pyamlboot.AmlogicSoC()

    print("Writing kernel...")
    dev.writeLargeMemory(UBOOT_IMAGEADDR, args.kernel.read(), 512, True)

    print("Writing dtb...")
    dev.writeLargeMemory(UBOOT_DTBADDR, args.dtb.read(), 512, True)

    if args.ramdisk is not None:
        print("Writing ramdisk...")
        dev.writeLargeMemory(UBOOT_INITRDADDR, args.ramdisk.read(), 512, True)

    if args.plain_image:
        bootcmd = "booti"
    else:
        bootcmd = "bootm"

    if args.no_escape:
        cmdline = args.cmdline
    else:
        # Roll our own escaping since U-Boot's hush is nonstandard enough that
        # shlex.quote() doesn't quite work right. Specifically, U-Boot removes
        # non-double backslashes from all strings, even single-quoted ones. But
        # it still doesn't allow backslashed-escaped single quotes in single-
        # quoted strings...
        cmdline = "'%s'" % (
            args.cmdline
                .replace("\\", "\\\\")
                .replace("'", "'\\''"),)

    print("Setting bootargs...")
    dev.tplCommand(1, "setenv bootargs " + cmdline)

    print("Running %s..." % (bootcmd,))
    if args.ramdisk is not None:
        dev.tplCommand(1, "%s 0x%x 0x%x 0x%x" % (bootcmd, UBOOT_IMAGEADDR, UBOOT_INITRDADDR, UBOOT_DTBADDR))
    else:
        dev.tplCommand(1, "%s 0x%x - 0x%x" % (bootcmd, UBOOT_IMAGEADDR, UBOOT_DTBADDR))
