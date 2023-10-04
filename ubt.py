#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0 OR MIT
# -*- coding: utf-8 -*-

__license__ = "GPL-2.0"
__copyright__ = "Copyright (c) 2024, SaluteDevices"
__version__ = '0.0.1'

import argparse
import logging
import sys
from enum import Enum

from adnl import do_adnl_burn
from aml_image_packer import AmlImagePack
from optimus import do_optimus_burn


class WipeFormat(Enum):
    no = 0
    normal = 1
    all = 3

    def __str__(self):
        return self.name


def main():
    logging.basicConfig(level=logging.DEBUG,
                        format='[%(asctime)s] [%(levelname)-8s]: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    parser = argparse.ArgumentParser()
    parser.add_argument('--img',
                        required=True,
                        type=argparse.FileType('rb'),
                        help='Specify location path to aml_upgrade_package.img')
    parser.add_argument('--reset',
                        action='store_true',
                        default=False,
                        help='Reset after success')
    parser.add_argument('--no-erase-bootloader',
                        action='store_true',
                        default=False,
                        help='Erase bootloader')
    parser.add_argument('--wipe',
                        type=lambda x: WipeFormat[x],
                        choices=list(WipeFormat),
                        default='no',
                        help='Destroy all partitions')
    parser.add_argument('--password',
                        type=argparse.FileType('rb'),
                        help='Unlock usb mode using password file provided')
    parser.add_argument('--version', action='version', version=__version__)

    args = parser.parse_args()
    aml_img = AmlImagePack(args.img)
    adnl = True

    # If image contains 'usb_flow', it is ADNL
    try:
        aml_img.item_get('aml', 'usb_flow')
    except ValueError:
        adnl = False

    if adnl:
        do_adnl_burn(args.reset, args.wipe.value, aml_img)
    else:
        do_optimus_burn(args, aml_img)


if __name__ == '__main__':
    sys.exit(main())
