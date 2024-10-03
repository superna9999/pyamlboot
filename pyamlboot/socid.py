# SPDX-License-Identifier: GPL-2.0 OR MIT
# -*- coding: utf-8 -*-
"""
Amlogic SocId parse Library

   Copyright (c) 2024, SaluteDevices

@author: Martin Kurbanov <mmkurbanov@salutedevices.com>
"""


class SocId:
    STAGE_MINOR_IPL = 0  # Initial Program Loader
    STAGE_MINOR_SPL = 8  # Secondary Program Loader
    STAGE_MINOR_TPL = 16  # Tertiary Program Loader

    def __init__(self, data):
        self._raw = data

    @property
    def major(self):
        return ord(self._raw[0])

    @property
    def minor(self):
        return ord(self._raw[1])

    @property
    def stage_major(self):
        return ord(self._raw[2])

    @property
    def stage_minor(self):
        return ord(self._raw[3])

    @property
    def need_password(self):
        assert len(self._raw) > 4
        return bool(ord(self._raw[4]))

    @property
    def password_ok(self):
        assert len(self._raw) > 5
        return bool(ord(self._raw[5]))

    def __str__(self):
        stage_names = {
            (0, self.STAGE_MINOR_IPL): 'IPL',
            (0, self.STAGE_MINOR_SPL): 'SPL',
            (0, self.STAGE_MINOR_TPL): 'TPL',
        }
        name = stage_names.get((self.stage_major, self.stage_minor), 'UNKNOWN')

        pad = ''
        for i in self._raw[4:]:
            pad += f'-{ord(i)}'

        return (f'{self.major}-{self.minor}-{self.stage_major}-'
                f'{self.stage_minor}{pad} ({name})')
