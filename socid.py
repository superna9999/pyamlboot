#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
# -*- coding: utf-8 -*-

from pyamlboot import pyamlboot

if __name__ == '__main__':
    dev = pyamlboot.AmlogicSoC()

    dev.nop()

    socid = dev.identify()

    print("Firmware Version :")
    print("ROM: %d.%d Stage: %d.%d" % (ord(socid[0]), ord(socid[1]), ord(socid[2]), ord(socid[3])))
    print("Need Password: %d Password OK: %d" % (ord(socid[4]), ord(socid[5])))
