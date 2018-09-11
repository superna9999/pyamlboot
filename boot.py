#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import sys
import os
from pyamlboot import pyamlboot

gx_boards = {"libretech-cc", "libretech-ac", "khadas-vim", "khadas-vim2", "odroid-c2", "nanopi-k2", "p212", "p230", "p231", "q200", "q201", "p281", "p241"}
axg_boards = {"s400", "s420"}

class BootParams:
    def __init__(self, board):
        self.UBOOT_SCRIPTADDR = 0x1f000000
        self.UBOOT_IMAGEADDR = 0x20080000
        self.UBOOT_DTBADDR = 0x20000000
        self.UBOOT_INITRDADDR = 0x26000000
        # GXBB/GXL/GXM params
        if board in gx_boards:
            print("Using GX Family boot parameters");
            self.DDR_LOAD = 0xd9000000
            self.BL2_PARAMS = 0xd900c000
            self.DDR_RUN = 0xd9000000
            self.UBOOT_LOAD = 0x200c000
            self.UBOOT_RUN = 0xd9000000 
        # AXG params
        elif board in axg_boards:
            print("Using AXG Family boot parameters");
            self.DDR_LOAD = 0xfffc0000
            self.BL2_PARAMS = 0xfffcc000
            self.DDR_RUN = 0xfffc0000
            self.UBOOT_LOAD = 0x200c000
            self.UBOOT_RUN = 0xfffc0000
        else:
            sys.stderr.write('Unsupported board %s, please fill boot parameters\n' % board)
            sys.exit(1)

DDR_FILE = 'files/usbbl2runpara_ddrinit.bin'
FIP_FILE = 'files/usbbl2runpara_runfipimg.bin'
BL2_FILE = 'files/%s/u-boot.bin.usb.bl2'
TPL_FILE = 'files/%s/u-boot.bin.usb.tpl'

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.stderr.write('Usage: %s <board model>\n' % sys.argv[0])
        sys.exit(1)

    params = BootParams(sys.argv[1])

    dev = pyamlboot.AmlogicSoC()

    socid = dev.identify()
    print("ROM: %d.%d Stage: %d.%d" % (ord(socid[0]), ord(socid[1]), ord(socid[2]), ord(socid[3])))

    print("Writing %s at 0x%x..." % ((BL2_FILE % sys.argv[1]), params.DDR_LOAD))
    with open((BL2_FILE % sys.argv[1]), "rb") as f:
        bl2 = f.read()
    dev.writeMemory(params.DDR_LOAD, bl2)
    print("[DONE]")

    print("Writing %s at 0x%x..." % (DDR_FILE, params.BL2_PARAMS))
    with open(DDR_FILE, "rb") as f:
        ddr = f.read()    
    dev.writeLargeMemory(params.BL2_PARAMS, ddr, 32)
    print("[DONE]")

    print("Running at 0x%x..." % params.DDR_RUN)
    dev.run(params.DDR_RUN)
    print("[DONE]")

    print("Waiting...");
    time.sleep(1)
    print("[DONE]")

    socid = dev.identify()
    print("ROM: %d.%d Stage: %d.%d" % (ord(socid[0]), ord(socid[1]), ord(socid[2]), ord(socid[3])))

    if ord(socid[3]) == 8:
        print("Running at 0x%x..." % params.BL2_PARAMS)
        dev.run(params.BL2_PARAMS)
        print("[DONE]")

        print("Waiting...");
        time.sleep(1)
        print("[DONE]")

    print("Writing %s at 0x%x..." % ((BL2_FILE % sys.argv[1]), params.DDR_LOAD))
    dev.writeLargeMemory(params.DDR_LOAD, bl2, 64)
    print("[DONE]")

    print("Writing %s at 0x%x..." % (FIP_FILE, params.BL2_PARAMS))
    with open(FIP_FILE, "rb") as f:
        fip = f.read()
    dev.writeLargeMemory(params.BL2_PARAMS, fip, 48)
    print("[DONE]")

    print("Writing %s at 0x%x..." % ((TPL_FILE % sys.argv[1]), params.UBOOT_LOAD))
    with open((TPL_FILE % sys.argv[1]), "rb") as f:
        tpl = f.read()
    dev.writeLargeMemory(params.UBOOT_LOAD, tpl, 64, True)
    print("[DONE]")

    if os.path.isfile("boot.scr"):
        print("Writing boot.scr at 0x%x..." % (params.UBOOT_SCRIPTADDR))
        with open("boot.scr", "rb") as f:
            script = f.read()
        dev.writeMemory(params.UBOOT_SCRIPTADDR, script)
        print("[DONE]")

    if os.path.isfile("Image"):
        print("Writing Image at 0x%x..." % (params.UBOOT_IMAGEADDR))
        with open("Image", "rb") as f:
            image = f.read()
        dev.writeLargeMemory(params.UBOOT_IMAGEADDR, image, 512, True)
        print("[DONE]")

    if os.path.isfile("%s.dtb" % sys.argv[1]):
        print("Writing %s.dtb at 0x%x..." % (sys.argv[1], params.UBOOT_DTBADDR))
        with open("%s.dtb" % sys.argv[1], "rb") as f:
            dtb = f.read()
        dev.writeMemory(params.UBOOT_DTBADDR, dtb)
        print("[DONE]")

    if os.path.isfile("rootfs.cpio.uboot"):
        print("Writing rootfs.cpio.uboot at 0x%x..." % (params.UBOOT_INITRDADDR))
        with open("rootfs.cpio.uboot", "rb") as f:
            rootfs = f.read()
        dev.writeLargeMemory(params.UBOOT_INITRDADDR, rootfs, 512, True)
        print("[DONE]")

    if ord(socid[3]) == 8:
        print("Running at 0x%x..." % params.BL2_PARAMS)
        dev.run(params.BL2_PARAMS)
        print("[DONE]")
    else:
        print("Running at 0x%x..." % params.UBOOT_RUN)
        dev.run(params.UBOOT_RUN)
        print("[DONE]")
