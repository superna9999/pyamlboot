#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
# -*- coding: utf-8 -*-

import argparse
import time
import os
import pkg_resources
from pyamlboot import pyamlboot

def list_boards(p):
    return [ d for d in os.listdir(p) if os.path.isdir(os.path.join(p, d)) and os.path.isfile(os.path.join(p, d, "u-boot.bin")) ]

def parse_wait(value):
    try:
        value = float(value)
    except:
        value = None
    return value

def parse_cmdline(fpath):
    boards = list_boards(fpath)
    parser = argparse.ArgumentParser(description="USB boot tool for Amlogic G12 SoCs",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--version', '-v', action='version', version='%(prog)s 1.0')
    parser.add_argument('binary',  action='store',
                        help="binary to load or name of board")
    parser.add_argument('--board-name', '-b', dest='bname',  action='store_true',
                        help="main argument becomes the name of the board to load (%s)" % boards)
    parser.add_argument('--timeout', type=parse_wait, action='store', default=0,
                        help="Timeout in seconds for device to enumerate")
    args = parser.parse_args()

    return args

if __name__ == '__main__':
    try:
        dist = pkg_resources.get_distribution('pyamlboot')
        fpath = os.path.join(dist.get_resource_filename(pkg_resources.ResourceManager(), "files")) 
    except:
        fpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "files")

    args = parse_cmdline(fpath)

    if args.bname:
        bpath = os.path.join(fpath, args.binary, "u-boot.bin")
    else:
        bpath = args.binary

    if args.timeout is None or args.timeout > 0:
        print("Waiting for device to enumerate...")

    dev = pyamlboot.AmlogicSoC(timeout=args.timeout)

    socid = dev.identify()

    print("Firmware Version :")
    print("ROM: %d.%d Stage: %d.%d" % (ord(socid[0]), ord(socid[1]), ord(socid[2]), ord(socid[3])))
    print("Need Password: %d Password OK: %d" % (ord(socid[4]), ord(socid[5])))

    loadAddr = 0xfffa0000
    with open(bpath, "rb") as f:
        seq = 0
        data = f.read()

        print("Writing %s at 0x%x..." % (bpath, loadAddr))
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
