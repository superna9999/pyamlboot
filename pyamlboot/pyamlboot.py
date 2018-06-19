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

REQ_WRITE_MEM = 0x01
REQ_READ_MEM = 0x02
REQ_FILL_MEM = 0x03
REQ_MODIFY_MEM = 0x04
REQ_RUN_IN_ADDR = 0x05
REQ_WRITE_AUX = 0x06
REQ_READ_AUX = 0x07

REQ_WR_LARGE_MEM = 0x11
REQ_RD_LARGE_MEM = 0x12
REQ_IDENTIFY_HOST = 0x20

REQ_TPL_CMD	= 0x30
REQ_TPL_STAT = 0x31

REQ_PASSWORD = 0x35
REQ_NOP = 0x36

FLAG_KEEP_POWER_ON = 0x10

class AmlogicSoC(object):
	"""Represents an Amlogic SoC in USB boot Mode"""

	def __init__(self, idVendor=0x1b8e, idProduct=0xc003):
		"""Init with vendor/product IDs"""

		self.dev = usb.core.find(idVendor=idVendor, idProduct=idProduct)

		if self.dev is None:
			raise ValueError('Device not found')

	def writeSimpleMemory(self, address, data):
		if len(data) > 64:
			raise ValueError('Maximum size of 64bytes')

		self.dev.ctrl_transfer(bmRequestType = 0x40, 
							   bRequest = REQ_WRITE_MEM,
							   wValue = address >> 16,
							   wIndex = address & 0xffff,
							   data_or_wLength = data)

	def writeMemory(self, address, data):
		length = len(data)
		offset = 0

		while length:
			self.writeSimpleMemory(address + offset, data[offset:offset+64])
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

		ret = self.dev.ctrl_transfer(0xc0, REQ_READ_MEM, address >> 16, address & 0xffff, length)

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

	# fillMemory
	# modifyMemory

	def run(self, address, keep_power=True):
		if keep_power:
			data = address | FLAG_KEEP_POWER_ON
		else:
			data = address
		controlData = pack('<I', data)
		self.dev.ctrl_transfer(0x40, REQ_RUN_IN_ADDR, address >> 16, address & 0xffff, controlData)

	# writeAux
	# readAux

	def writeLargeMemory(self, address, data, blockLength=64, appendZeros=False):
		if appendZeros:
			append = len(data) % blockLength
			data = data + pack('b', 0) * append
		elif len(data) % blockLength != 0:
			raise ValueError('Large Data must be a multiple of block length')

		blockCount = int(len(data) / blockLength)
		controlData = pack('<IIII', address, len(data), 0, 0)

		offset = 0

		cfg = self.dev.get_active_configuration()
		intf = cfg[(0,0)]
		ep = usb.util.find_descriptor(
						intf,
						# match the first OUT endpoint
						custom_match = \
						lambda e: \
						usb.util.endpoint_direction(e.bEndpointAddress) == \
						usb.util.ENDPOINT_OUT)

		self.dev.ctrl_transfer(0x40, REQ_WR_LARGE_MEM, blockLength, blockCount, controlData)

		while blockCount > 0:
			ep.write(data[offset:offset+blockLength], 100)
			offset = offset + blockLength
			blockCount = blockCount - 1

	def readLargeMemory(self, address, length, blockLength=64, appendZeros=False):
		if appendZeros:
			length = length + (length % blockLength)
		elif length % blockLength != 0:
			raise ValueError('Large Data must be a multiple of block length')

		blockCount = int(length / blockLength)
		controlData = pack('<IIII', address, length, 0, 0)
		data = ''

		cfg = self.dev.get_active_configuration()
		intf = cfg[(0,0)]
		ep = usb.util.find_descriptor(
						intf,
						# match the first OUT endpoint
						custom_match = \
						lambda e: \
						usb.util.endpoint_direction(e.bEndpointAddress) == \
						usb.util.ENDPOINT_IN)

		self.dev.ctrl_transfer(0x40, REQ_RD_LARGE_MEM, blockLength, blockCount, controlData)

		while blockCount > 0:
			data = data + ''.join(map(chr,ep.read(blockLength, 100)))
			blockCount = blockCount - 1

		return data

	def identify(self):
		ret = self.dev.ctrl_transfer(0xc0, REQ_IDENTIFY_HOST, 0, 0, 8)

		return ''.join([chr(x) for x in ret])

	# tplCommand
	# tplStat

	def sendPassword(self, password):
		if length != 64:
			raise ValueError('Password size is 64bytes')
		controlData = [ord(elem) for elem in password]
		self.dev.ctrl_transfer(0x40, REQ_PASSWORD, 0, 0, controlData)

	def nop(self):
		self.dev.ctrl_transfer(0x40, REQ_NOP, 0, 0, None)
