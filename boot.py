#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
# -*- coding: utf-8 -*-

import argparse
import time
import sys
import os
import pkg_resources
from pyamlboot import pyamlboot

gx_boards = {"libretech-s905x-cc", "libretech-s805x-ac", "khadas-vim", "khadas-vim2", "odroid-c2", "nanopi-k2", "p212", "p230", "p231", "q200", "q201", "p281", "p241", "libretech-s912-pc", "libretech-s905d-pc"}
axg_boards = {"s400", "s420", "apollo" }

class BootUSB:
    def __init__(self, board, fpath, upath):
        self.UBOOT_SCRIPTADDR = 0x8000000
        self.UBOOT_IMAGEADDR = 0x8080000
        self.UBOOT_DTBADDR = 0x8008000
        self.UBOOT_INITRDADDR = 0x13000000
        self.DDR_FILE = 'usbbl2runpara_ddrinit.bin'
        self.FIP_FILE = 'usbbl2runpara_runfipimg.bin'
        self.BL2_FILE = 'u-boot.bin.usb.bl2'
        self.TPL_FILE = 'u-boot.bin.usb.tpl'

        # GXBB/GXL/GXM params
        if board in gx_boards:
            print("Using GX Family boot parameters");
            self.DDR_LOAD = 0xd9000000
            self.BL2_PARAMS = 0xd900c000
            self.UBOOT_LOAD = 0x200c000
        # AXG params
        elif board in axg_boards:
            print("Using AXG Family boot parameters");
            self.DDR_LOAD = 0xfffc0000
            self.BL2_PARAMS = 0xfffcc000
            self.UBOOT_LOAD = 0x200c000
        else:
            sys.stderr.write('Unsupported board %s, please fill boot parameters\n' % board)
            sys.exit(1)

        self.dev = pyamlboot.AmlogicSoC()
        self.fpath = fpath
        if upath:
            self.bpath = upath
        else:
            self.bpath = os.path.join(fpath, board)

    def wait(self, t):
        print("Waiting...");
        time.sleep(t)
        print("[DONE]")

    def soc_id(self):
        s = self.dev.identify()
        print("ROM: %d.%d Stage: %d.%d" % (ord(s[0]), ord(s[1]), ord(s[2]), ord(s[3])))
        self.socid = s

    def write_file(self, path, addr, large = None, fill = False):
        print("Writing %s at 0x%x..." % (path, addr))
        with open(path, "rb") as f:
            b = f.read()
        if large is not None:
            self.dev.writeLargeMemory(addr, b, large, fill)
        else:
            self.dev.writeMemory(addr, b)
        print("[DONE]")

    def run(self, addr):
        print("Running at 0x%x..." % addr)
        self.dev.run(addr)
        print("[DONE]")

    def init_ddr(self):
        self.soc_id()
        self.write_file(os.path.join(self.bpath, self.BL2_FILE), self.DDR_LOAD)
        self.write_file(os.path.join(self.fpath, self.DDR_FILE), self.BL2_PARAMS, large = 32)
        self.run(self.DDR_LOAD)
        self.wait(1)

        self.soc_id()
        if ord(self.socid[3]) == 8:
            self.run(self.BL2_PARAMS)
            self.wait(1)

    def load_uboot(self):
        self.init_ddr()
        self.write_file(os.path.join(self.bpath, self.BL2_FILE), self.DDR_LOAD, large = 64)
        self.write_file(os.path.join(self.fpath, self.FIP_FILE), self.BL2_PARAMS, large = 48)
        self.write_file(os.path.join(self.bpath, self.TPL_FILE), self.UBOOT_LOAD, large = 64, fill = True)

    def run_uboot(self):
        if ord(self.socid[3]) == 8:
            self.run(self.BL2_PARAMS)
        else:
            self.run(self.DDR_LOAD)

def list_boards(p):
    return [ d for d in os.listdir(p) if os.path.isdir(os.path.join(p, d)) and (d in gx_boards or d in axg_boards) ]

def parse_cmdline(boards):
    parser = argparse.ArgumentParser(description="USB boot tool for Amlogic",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--version', '-v', action='version', version='%(prog)s 1.0')
    parser.add_argument('board',  action='store', choices=boards,
                        help="board type to boot on")
    parser.add_argument('--board-files', dest='upath',  action='store',
                        help="Path to Board files")
    parser.add_argument('--image', dest='imagefile',  action='store',
                        help="image file to load")
    parser.add_argument('--script', dest='scriptfile',  action='store',
                        help="script file to load")
    parser.add_argument('--fdt', dest='dtbfile',  action='store',
                        help="dtb file to load")
    parser.add_argument('--ramfs', dest='ramfsfile',  action='store',
                        help="ramfs file to load")

    args = parser.parse_args()

    return args

if __name__ == '__main__':
    # Try to get boot files from the python package, or from local tree
    try:
        dist = pkg_resources.get_distribution('pyamlboot')
        fpath = dist.get_resource_filename(pkg_resources.ResourceManager(), "files")
    except:
        fpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "files")
    boards = list_boards(fpath)
    args = parse_cmdline(boards)
    usb = BootUSB(args.board, fpath, args.upath)

    usb.load_uboot()

    if args.imagefile is not None:
        usb.write_file(args.imagefile, usb.UBOOT_IMAGEADDR, 512, True)

    if args.dtbfile is not None:
        usb.write_file(args.dtbfile, usb.UBOOT_DTBADDR)

    if args.scriptfile is not None:
        usb.write_file(args.scriptfile, usb.UBOOT_SCRIPTADDR)

    if args.ramfsfile is not None:
        usb.write_file(args.ramfsfile, usb.UBOOT_INITRDADDR, 512, True)

    usb.run_uboot()
