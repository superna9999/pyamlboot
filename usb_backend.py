# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0 OR MIT

__license__ = "GPL-2.0"
__copyright__ = "Copyright (c) 2024, SaluteDevices"

import logging
import sys

import usb.backend.libusb1 as libusb1
import usb.backend.libusb0 as libusb0

__all__ = ['get_backend']

_logger = logging.getLogger('usb.backend')


class _LibUSB:
    def __init__(self, backend):
        self._backend = backend
        self._stub_func = {
            'get_configuration': self._get_configuration
        }

        if sys.platform == 'linux':
            self._stub_func.update({
                'set_interface_altsetting': self._stub,
                'claim_interface': self._stub,
                'release_interface': self._stub,
            })

    def _stub(self, *args, **kwargs):
        pass

    def _get_configuration(self, dev_handle):
        return 1

    def __getattr__(self, item):
        if item in self._stub_func:
            return self._stub_func[item]

        return getattr(self._backend, item)


def get_backend(find_library=None):
    backends = [libusb0]
    if sys.platform == 'win32':
        backends.insert(0, libusb1)

    for m in backends:
        backend = m.get_backend()
        if backend is not None:
            _logger.info('find(): using backend "%s"', m.__name__)
            break
    else:
        return None

    return _LibUSB(backend)
