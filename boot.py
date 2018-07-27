#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import sys
from pyamlboot import pyamlboot

DDR_LOAD = 0xd9000000
BL2_PARAMS = 0xd900c000
DDR_RUN = 0xd9000000
UBOOT_LOAD = 0x200c000
UBOOT_RUN = 0xd9000000

DDR_FILE = 'files/usbbl2runpara_ddrinit.bin'
FIP_FILE = 'files/usbbl2runpara_runfipimg.bin'
BL2_FILE = 'files/%s/u-boot.bin.usb.bl2'
TPL_FILE = 'files/%s/u-boot.bin.usb.tpl'

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.stderr.write('Usage: %s <board model>\n' % sys.argv[0])
        sys.exit(1)

    dev = pyamlboot.AmlogicSoC()

    socid = dev.identify()
    print("ROM: %d.%d Stage: %d.%d" % (ord(socid[0]), ord(socid[1]), ord(socid[2]), ord(socid[3])))

    print("Writing %s at 0x%x..." % ((BL2_FILE % sys.argv[1]), DDR_LOAD))
    with open((BL2_FILE % sys.argv[1]), "rb") as f:
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
    time.sleep(2)
    print("[DONE]")

    socid = dev.identify()
    print("ROM: %d.%d Stage: %d.%d" % (ord(socid[0]), ord(socid[1]), ord(socid[2]), ord(socid[3])))

    if ord(socid[3]) == 8:
        print("Running at 0x%x..." % BL2_PARAMS)
        dev.run(BL2_PARAMS)
        print("[DONE]")

        print("Waiting...");
        time.sleep(2)
        print("[DONE]")

    print("Writing %s at 0x%x..." % ((BL2_FILE % sys.argv[1]), DDR_LOAD))
    dev.writeLargeMemory(DDR_LOAD, bl2, 64)
    print("[DONE]")

    print("Writing %s at 0x%x..." % (FIP_FILE, BL2_PARAMS))
    with open(FIP_FILE, "rb") as f:
        fip = f.read()
    dev.writeLargeMemory(BL2_PARAMS, fip, 48)
    print("[DONE]")

    print("Writing %s at 0x%x..." % ((TPL_FILE % sys.argv[1]), UBOOT_LOAD))
    with open((TPL_FILE % sys.argv[1]), "rb") as f:
        tpl = f.read()
    dev.writeLargeMemory(UBOOT_LOAD, tpl, 64, True)
    print("[DONE]")

    if ord(socid[3]) == 8:
        print("Running at 0x%x..." % BL2_PARAMS)
        dev.run(BL2_PARAMS)
        print("[DONE]")
    else:
        print("Running at 0x%x..." % UBOOT_RUN)
        dev.run(UBOOT_RUN)
        print("[DONE]")
