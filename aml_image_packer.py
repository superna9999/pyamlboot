#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0 OR MIT
# -*- coding: utf-8 -*-

__license__ = "GPL-2.0"
__copyright__ = "Copyright (c) 2024, SaluteDevices"

import os
import sys
from pyamlboot.amlimage import AmlImagePack


if __name__ == '__main__':
    if len(sys.argv) < 2:
        prog = os.path.basename(sys.argv[0])
        print(f'usage: {prog} aml_upgrade_package.img')
        sys.exit(0)

    img = AmlImagePack(sys.argv[1])

    main_type_max_len = 0
    sub_type_max_len = 0
    file_type_max_len = 0

    for item in img.items():
        main_type_max_len = max(main_type_max_len, len(item.main_type()))
        sub_type_max_len = max(sub_type_max_len, len(item.sub_type()))
        file_type_max_len = max(file_type_max_len, len(item.file_type()))

    for item in img.items():
        print(f'main_type:{item.main_type():<{main_type_max_len}} '
              f'sub_type:{item.sub_type():<{sub_type_max_len}} '
              f'file_type:{item.file_type():<{file_type_max_len}} '
              f'is_verify:{item.is_verify()!s:<5} '
              f'size:{item.size()}')
