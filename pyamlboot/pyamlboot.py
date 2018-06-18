# -*- coding: utf-8 -*-
"""
Amlogic USB Boot Protocol Library

   Copyright 2018 BayLibre SAS
   Author: Neil Armstrong <narmstrong@baylibre.com>

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

@author: Neil Armstrong <narmstrong@baylibre.com>
"""

import string
import os
import usb.core
import usb.util
from struct import Struct, unpack, pack

class AmlogicSoC(object):
	"""Represents an Amlogic SoC in USB boot Mode"""

	def __init__(self, idVendor=0x1b8e, idProduct=0xc003):
		"""Init with vendor/product IDs"""

		self.dev = usb.core.find(idVendor=idVendor, idProduct=idProduct)

		if self.dev is None:
			raise ValueError('Device not found')

		self.dev.set_configuration()

	def writeSimpleMemory(self, address, data):
		if len(data) > 64:
			raise ValueError('Maximum size of 64bytes')

		self.dev.ctrl_transfer(0x40, 1, address >> 16, address & 0xffff, data)

	def writeMemory(self, address, data):
		length = len(data)
		offset = 0

		while length:
			self.writeSimpleMemory(self, address + offset, data[offset:offset+64])
			if length > 64:
				length = length - 64
			else:
				break
			offset = offset + 64

	def readSimpleMemory(self, address, length):
		if length == 0:
			return ''

		if length > 64:
			raise ValueError('Maximum size of 64bytes')

		ret = self.dev.ctrl_transfer(0xc0, 2, address >> 16, address & 0xffff, length)

		return ''.join([chr(x) for x in ret])

	def readMemory(self, address, length):
		data = ''
		offset = 0

		while length:
			if length >= 64:
				data = data + self.readSimpleMemory(address + offset, 64)
				length = length - 64
				offset = offset + 64
			else:
				data = data + self.readSimpleMemory(address + offset, length)
				break

		return data

	def identify(self):
		ret = self.dev.ctrl_transfer(0xc0, 32, 0, 0, 8)

		return ''.join([chr(x) for x in ret])

	def run(self, address):
		data = pack('>I', address | 0x10)
		self.dev.ctrl_transfer(0x40, 5, address >> 16, address & 0xffff, data)
