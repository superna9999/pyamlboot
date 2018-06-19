#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from pyamlboot import pyamlboot

DDR_LOAD = 0xd9000000
BL2_PARAMS = 0xd900c000
DDR_RUN = 0xd9000000
UBOOT_LOAD = 0x200c000
UBOOT_RUN = 0xd9000000

DDR_FILE = 'files/usbbl2runpara_ddrinit.bin'
FIP_FILE = 'files/usbbl2runpara_runfipimg.bin'
BL2_FILE = 'files/u-boot.bin.usb.bl2'
TPL_FILE = 'files/u-boot.bin.usb.tpl'

if __name__ == '__main__':
    dev = pyamlboot.AmlogicSoC()

    print("Writing %s at 0x%x..." % (BL2_FILE, DDR_LOAD))
    with open(BL2_FILE, "rb") as f:
        bl2 = f.read()
    dev.writeMemory(DDR_LOAD, bl2)
    print("[DONE]")

    print("Writing %s at 0x%x..." % (DDR_FILE, BL2_PARAMS))
    with open(DDR_FILE, "rb") as f:
        ddr = f.read()    
    dev.writeLargeMemory(BL2_PARAMS, ddr, 32)
    print("[DONE]")

    print("Running at 0x%x..." % DDR_RUN)
    dev.run(DDR_RUN)
    print("[DONE]")

    print("Waiting...");
    time.sleep(1)
    print("[DONE]")

    print("Writing %s at 0x%x..." % (BL2_FILE, DDR_LOAD))
    dev.writeLargeMemory(DDR_LOAD, bl2, 64)
    print("[DONE]")

    print("Writing %s at 0x%x..." % (FIP_FILE, BL2_PARAMS))
    with open(FIP_FILE, "rb") as f:
        fip = f.read()
    dev.writeLargeMemory(BL2_PARAMS, fip, 48)
    print("[DONE]")

    print("Writing %s at 0x%x..." % (TPL_FILE, UBOOT_LOAD))
    with open(TPL_FILE, "rb") as f:
        tpl = f.read()
    dev.writeLargeMemory(UBOOT_LOAD, tpl, 64, True)
    print("[DONE]")

    print("Running at 0x%x..." % UBOOT_RUN)
    dev.run(UBOOT_RUN)
    print("[DONE]")
