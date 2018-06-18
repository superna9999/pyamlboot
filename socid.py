#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pyamlboot import pyamlboot

if __name__ == '__main__':
    dev = pyamlboot.AmlogicSoC()
    socid = dev.identify()

    print("Firmware Version :")
    print("%d-%d-%d-%d" % (ord(socid[0]), ord(socid[1]), ord(socid[2]), ord(socid[3])))
