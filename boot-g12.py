#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import time
from pyamlboot import pyamlboot

def parse_cmdline():
    parser = argparse.ArgumentParser(description="USB boot tool for Amlogic G12 SoCs",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--version', '-v', action='version', version='%(prog)s 1.0')
    parser.add_argument('binary',  action='store',
                        help="binary to load")
    args = parser.parse_args()

    return args

if __name__ == '__main__':
    args = parse_cmdline()

    dev = pyamlboot.AmlogicSoC()

    socid = dev.identify()

    print("Firmware Version :")
    print("ROM: %d.%d Stage: %d.%d" % (ord(socid[0]), ord(socid[1]), ord(socid[2]), ord(socid[3])))
    print("Need Password: %d Password OK: %d" % (ord(socid[4]), ord(socid[5])))

    loadAddr = 0xfffa0000
    with open(args.binary, "rb") as f:
        seq = 0
        data = f.read()

        print("Writing %s at 0x%x..." % (args.binary, loadAddr))
        dev.writeLargeMemory(0xfffa0000, data[0:0x10000], 4096)
        print("[DONE]")

        print("Running at 0x%x..." % loadAddr)
        dev.run(0xfffa0000)
        print("[DONE]")

        time.sleep(2)

        prevLength = -1
        prevOffset = -1
        while True:
            (length, offset) = dev.getBootAMLC()

            if length == prevLength and offset == prevOffset:
                print("[BL2 END]")
                break

            prevLength = length
            prevOffset = offset

            print("AMLC dataSize=%d, offset=%d, seq=%d..." % (length, offset, seq))
            dev.writeAMLCData(seq, offset, data[offset:offset+length])
            print("[DONE]")

            seq = seq + 1
