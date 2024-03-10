# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""
Amlogic USB Boot Protocol Library

   Copyright 2018 BayLibre SAS

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

REQ_TPL_CMD    = 0x30
REQ_TPL_STAT = 0x31

REQ_WRITE_MEDIA = 0x32
REQ_READ_MEDIA = 0x33

REQ_BULKCMD = 0x34

REQ_PASSWORD = 0x35
REQ_NOP = 0x36

REQ_GET_AMLC = 0x50
REQ_WRITE_AMLC = 0x60

FLAG_KEEP_POWER_ON = 0x10

AMLC_AMLS_BLOCK_LENGTH = 0x200
AMLC_MAX_BLOCK_LENGTH = 0x4000
AMLC_MAX_TRANSFERT_LENGTH = 65536

MAX_LARGE_BLOCK_COUNT = 65535

WRITE_MEDIA_CHEKSUM_ALG_NONE = 0x00ee
WRITE_MEDIA_CHEKSUM_ALG_ADDSUM = 0x00ef
WRITE_MEDIA_CHEKSUM_ALG_CRC32 = 0x00f0

class AmlogicSoC(object):
    """Represents an Amlogic SoC in USB boot Mode"""

    def __init__(self, idVendor=0x1b8e, idProduct=0xc003, usb_backend=None):
        """Init with vendor/product IDs"""

        self.dev = usb.core.find(idVendor=idVendor,
                                 idProduct=idProduct,
                                 backend=usb_backend)

        if self.dev is None:
            raise ValueError('Device not found')

    def writeSimpleMemory(self, address, data):
        """Write a chunk of data to memory"""
        if len(data) > 64:
            raise ValueError('Maximum size of 64bytes')

        self.dev.ctrl_transfer(bmRequestType = 0x40,
                               bRequest = REQ_WRITE_MEM,
                               wValue = address >> 16,
                               wIndex = address & 0xffff,
                               data_or_wLength = data)

    def writeMemory(self, address, data):
        """Write some data to memory"""
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
        """Read a chunk of data from memory"""
        if length == 0:
            return ''

        if length > 64:
            raise ValueError('Maximum size of 64bytes')

        ret = self.dev.ctrl_transfer(bmRequestType = 0xc0,
                                     bRequest = REQ_READ_MEM,
                                     wValue = address >> 16,
                                     wIndex = address & 0xffff,
                                     data_or_wLength = length)

        return ret

    def readMemory(self, address, length):
        """Read some data from memory"""
        data = bytes()
        offset = 0

        while length:
            if length >= 64:
                data = data.append(self.readSimpleMemory(address + offset, 64))
                length = length - 64
                offset = offset + 64
            else:
                data += self.readSimpleMemory(address + offset, length)
                break

        return data

    # fillMemory
    def modifyMemory(self, opcode, address1, data, mask, address2):
        """UNTESTED: Modify memory with a pattern"""
        controlData = pack('<IIII', address1, data, mask, address2)

        self.dev.ctrl_transfer(bmRequestType = 0x40,
                               bRequest = REQ_MODIFY_MEM,
                               wValue = opcode,
                               wIndex = 0,
                               data_or_wLength = controlData)

    def readReg(self, address):
        """Read value at address"""
        reg = self.readSimpleMemory(address, 4)
        return int.from_bytes(reg, byteorder='little')

    def writeReg(self, address, value):
        """UNTESTED: Write value at address"""
        self.modifyMemory(0, address, value, 0, 0)

    def maskRegAND(self, address, mask):
        """UNTESTED: read/AND mask/write address"""
        self.modifyMemory(1, address, 0, mask, 0)

    def maskRegOR(self, address, mask):
        """UNTESTED: read/OR mask/write address"""
        self.modifyMemory(2, address, 0, mask, 0)

    def maskRegNAND(self, address, mask):
        """UNTESTED: read/AND NOT mask/write address"""
        self.modifyMemory(3, address, 0, mask, 0)

    def writeRegBits(self, address, mask, value):
        """UNTESTED: read/(AND NOT mask) OR (data AND mask)/write address"""
        self.modifyMemory(4, address, value, mask, 0)

    def copyReg(self, source, dest):
        """UNTESTED: read at source address and write it into dest address"""
        self.modifyMemory(5, dest, 0, 0, source)

    def copyRegMaskAND(self, source, dest, mask):
        """UNTESTED: read source/AND mask/write dest"""
        self.modifyMemory(6, dest, 0, mask, source)

    def memcpy(self, dest, src, n):
        """UNTESTED: copy n words from src to dest"""
        self.modifyMemory(7, src, n, 0, dest)

    def run(self, address, keep_power=True):
        """Run code from memory"""
        if keep_power:
            data = address | FLAG_KEEP_POWER_ON
        else:
            data = address
        controlData = pack('<I', data)
        self.dev.ctrl_transfer(bmRequestType = 0x40,
                               bRequest = REQ_RUN_IN_ADDR,
                               wValue = address >> 16,
                               wIndex = address & 0xffff,
                               data_or_wLength = controlData)

    # writeAux
    # readAux

    def _writeLargeMemory(self, address, data, blockLength=64, appendZeros=False):
        if appendZeros:
            append = len(data) % blockLength
            data = data + pack('b', 0) * append
        elif len(data) % blockLength != 0:
            raise ValueError('Large Data must be a multiple of block length')

        blockCount = int(len(data) / blockLength)
        if len(data) % blockLength > 0:
            blockCount = blockCount + 1
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

        self.dev.ctrl_transfer(bmRequestType = 0x40,
                               bRequest = REQ_WR_LARGE_MEM,
                               wValue = blockLength,
                               wIndex = blockCount,
                               data_or_wLength = controlData)

        while blockCount > 0:
            ep.write(data[offset:offset+blockLength], 1000)
            offset = offset + blockLength
            blockCount = blockCount - 1

    def writeLargeMemory(self, address, data, blockLength=64, appendZeros=False):
        """Write some data to memory, for large transfers with a programmable block length"""
        blockCount = int(len(data) / blockLength)
        if len(data) % blockLength > 0:
            blockCount = blockCount + 1
        transferCount = int(blockCount / MAX_LARGE_BLOCK_COUNT)
        if blockCount % MAX_LARGE_BLOCK_COUNT > 0:
            transferCount = transferCount + 1
        offset = 0

        while transferCount > 0:
            if (offset + (MAX_LARGE_BLOCK_COUNT * blockLength)) > len(data):
                writeLength = len(data) - offset
            else:
                writeLength = (MAX_LARGE_BLOCK_COUNT * blockLength)
            self._writeLargeMemory(address+offset, data[offset:offset+writeLength], \
                                   blockLength, appendZeros)
            offset = offset + writeLength
            transferCount = transferCount - 1

    def _readLargeMemory(self, address, length, blockLength=64, appendZeros=False):
        """Read some data from memory, for large transfers with a programmable block length"""
        if appendZeros:
            length = length + (length % blockLength)
        elif length % blockLength != 0:
            raise ValueError('Large Data must be a multiple of block length')

        blockCount = int(length / blockLength)
        if length % blockLength > 0:
            blockCount = blockCount + 1
        controlData = pack('<IIII', address, length, 0, 0)
        data = bytes()

        cfg = self.dev.get_active_configuration()
        intf = cfg[(0,0)]
        ep = usb.util.find_descriptor(
                        intf,
                        # match the first OUT endpoint
                        custom_match = \
                        lambda e: \
                        usb.util.endpoint_direction(e.bEndpointAddress) == \
                        usb.util.ENDPOINT_IN)

        self.dev.ctrl_transfer(bmRequestType = 0x40,
                               bRequest = REQ_RD_LARGE_MEM,
                               wValue = blockLength,
                               wIndex = blockCount,
                               data_or_wLength = controlData)

        while blockCount > 0:
            data += ep.read(blockLength, 100)
            blockCount = blockCount - 1

        return data

    def readLargeMemory(self, address, length, blockLength=64, appendZeros=False):
        """Read some data from memory, for large transfers with a programmable block length"""
        blockCount = int(length / blockLength)
        if length % blockLength > 0:
            blockCount = blockCount + 1
        transferCount = int(blockCount / MAX_LARGE_BLOCK_COUNT)
        if blockCount % MAX_LARGE_BLOCK_COUNT > 0:
            transferCount = transferCount + 1
        offset = 0
        data = bytes()

        while transferCount > 0:
            if (offset + (MAX_LARGE_BLOCK_COUNT * blockLength)) > length:
                readLength = length - offset
            else:
                readLength = (MAX_LARGE_BLOCK_COUNT * blockLength)
            data += self._readLargeMemory(address+offset, readLength, \
                                                blockLength, appendZeros)
            offset = offset + readLength
            transferCount = transferCount - 1

        return data

    def identify(self):
        """Identify the ROM Protocol"""
        ret = self.dev.ctrl_transfer(bmRequestType = 0xc0,
                                     bRequest = REQ_IDENTIFY_HOST,
                                     wValue = 0, wIndex = 0,
                                     data_or_wLength = 8)

        return ''.join([chr(x) for x in ret])

    def tplCommand(self, subcode, command):
        terminated_cmd = command + '\0'

        # U-Boot's USB function gets confused if the string is longer than this.
        # Not sure why.
        if len(terminated_cmd) >= 128:
            raise ValueError("TPL command must be shorter than 127 characters")

        self.dev.ctrl_transfer(bmRequestType = 0x40,
                               bRequest = REQ_TPL_CMD,
                               wValue = 0, wIndex = subcode,
                               data_or_wLength = terminated_cmd)

    # tplStat
    def tplStat(self, timeout=None):
        return self.dev.ctrl_transfer(bmRequestType=0xc0,
                                      bRequest=REQ_TPL_STAT,
                                      wValue=0,
                                      wIndex=0,
                                      data_or_wLength=0x40,
                                      timeout=timeout)

    def sendPassword(self, password):
        """UNTESTED: Send password"""
        if isinstance(password, str):
            controlData = [ord(elem) for elem in password]
        else:
            controlData = password

        self.dev.ctrl_transfer(bmRequestType = 0x40,
                               bRequest = REQ_PASSWORD,
                               wValue = 0, wIndex = 0,
                               data_or_wLength = controlData)

    def nop(self):
        """No-Operation, for testing purposes"""
        self.dev.ctrl_transfer(bmRequestType = 0x40,
                               bRequest = REQ_NOP,
                               wValue = 0, wIndex = 0,
                               data_or_wLength = None)

    def getBootAMLC(self):
        """Read BL2 Boot AMLC Data Request"""

        cfg = self.dev.get_active_configuration()
        intf = cfg[(0,0)]
        epout = usb.util.find_descriptor(
                        intf,
                        # match the first OUT endpoint
                        custom_match = \
                        lambda e: \
                        usb.util.endpoint_direction(e.bEndpointAddress) == \
                        usb.util.ENDPOINT_OUT)
        epin = usb.util.find_descriptor(
                        intf,
                        # match the first OUT endpoint
                        custom_match = \
                        lambda e: \
                        usb.util.endpoint_direction(e.bEndpointAddress) == \
                        usb.util.ENDPOINT_IN)

        self.dev.ctrl_transfer(bmRequestType = 0x40,
                               bRequest = REQ_GET_AMLC,
                               wValue = AMLC_AMLS_BLOCK_LENGTH,
                               wIndex = 0,
                               data_or_wLength = None)

        data = epin.read(AMLC_AMLS_BLOCK_LENGTH, 100)
        (tag, length, offset) = unpack('<4s4xII', data[0:16])

        if not "AMLC" in ''.join(map(chr,tag)):
            raise ValueError('Invalid AMLC Request %s' % data[0:16])

        # Ack the request
        okay = pack('<4sIII', bytes("OKAY", 'ascii'), 0, 0, 0)
        epout.write(okay, 1000)

        return (length, offset)

    def _writeAMLCData(self, offset, data):
        """Write AMLC data block, or final AMLS"""
        dataOffset = 0
        writeLength = len(data)
        blockCount = int(writeLength / AMLC_MAX_BLOCK_LENGTH)
        if len(data) % AMLC_MAX_BLOCK_LENGTH > 0:
            blockCount = blockCount + 1

        cfg = self.dev.get_active_configuration()
        intf = cfg[(0,0)]
        epout = usb.util.find_descriptor(
                        intf,
                        # match the first OUT endpoint
                        custom_match = \
                        lambda e: \
                        usb.util.endpoint_direction(e.bEndpointAddress) == \
                        usb.util.ENDPOINT_OUT)
        epin = usb.util.find_descriptor(
                        intf,
                        # match the first OUT endpoint
                        custom_match = \
                        lambda e: \
                        usb.util.endpoint_direction(e.bEndpointAddress) == \
                        usb.util.ENDPOINT_IN)

        self.dev.ctrl_transfer(bmRequestType = 0x40,
                               bRequest = REQ_WRITE_AMLC,
                               wValue = int(offset / AMLC_AMLS_BLOCK_LENGTH),
                               wIndex = writeLength - 1,
                               data_or_wLength = None)

        while blockCount > 0:
            remain = writeLength - dataOffset
            if remain > AMLC_MAX_BLOCK_LENGTH:
                blockLength = AMLC_MAX_BLOCK_LENGTH
            else:
                blockLength = remain
            epout.write(data[dataOffset:dataOffset+blockLength], 1000)
            dataOffset = dataOffset + blockLength
            blockCount = blockCount - 1

        # Wait for Ack
        data = epin.read(16, 1000)

        if not "OKAY" in ''.join(map(chr,data[0:4])):
            raise ValueError('Invalid AMLC Data Write Ack %s' % data)

    def _amlsChecksum(self, data):
        """Calculate data checksum for AMLS"""
        checksum = 0
        offset = 0
        uint32_max = (1 << 32)

        while offset < len(data):
            left = len(data) - offset
            if left >= 4:
                val = unpack('<I', data[offset:offset+4])[0]
            elif left >= 3:
                val = unpack('<I', data[offset:offset+4].ljust(4, b'\x00'))[0] & 0xffffff
            elif left >= 2:
                val = unpack('<H', data[offset:offset+2])[0]
            else:
                val = unpack('<B', data[offset])[0]
            offset = offset + 4
            checksum = (checksum + abs(val)) % uint32_max

        return checksum

    def writeAMLCData(self, seq, amlcOffset, data):
        """Write Request AMLC Data"""
        dataLen = len(data)
        transferCount = int(dataLen / AMLC_MAX_TRANSFERT_LENGTH)
        if dataLen % AMLC_MAX_TRANSFERT_LENGTH > 0:
            transferCount = transferCount + 1
        offset = 0

        while transferCount > 0:
            if (offset + AMLC_MAX_TRANSFERT_LENGTH) > dataLen:
                writeLength = dataLen - offset
            else:
                writeLength = AMLC_MAX_TRANSFERT_LENGTH
            self._writeAMLCData(offset, data[offset:offset+writeLength])
            offset = offset + writeLength
            transferCount = transferCount - 1

        # Write AMLS with checksum over full block, while transferring part of the first 512 bytes
        checksum = self._amlsChecksum(data)
        amls = pack('<4sBBBBII', bytes("AMLS", 'ascii'), seq, 0, 0, 0, checksum, 0) + data[16:512]
        self._writeAMLCData(amlcOffset, amls)

    @staticmethod
    def _endpoint_match_in(ep):
        return usb.util.endpoint_direction(ep.bEndpointAddress) ==\
               usb.util.ENDPOINT_IN

    @staticmethod
    def _endpoint_match_out(ep):
        return usb.util.endpoint_direction(ep.bEndpointAddress) ==\
               usb.util.ENDPOINT_OUT

    def readMedia(self, size, timeout=None):
        """Read data from storage

        Before reading data, you need to specify:
            - where to read (partitions, mem)
            - type of reading data
            - size of data
        For that need to use Bulk command 'upload'
        """
        block_length = 0x1000
        cfg = self.dev.get_active_configuration()
        intf = cfg[(0, 0)]

        epin = usb.util.find_descriptor(intf,
                                        custom_match=self._endpoint_match_in)

        controlData = pack('<IIII', 0, size, 0, 0)
        blocks = (block_length + size - 1) // block_length

        self.dev.ctrl_transfer(bmRequestType=0xc0,
                               bRequest=REQ_READ_MEDIA,
                               wValue=size,
                               wIndex=blocks,
                               data_or_wLength=controlData)

        return epin.read(size, timeout=timeout).tobytes()

    def writeMedia(self, data, ackLen=0x200, seq=0, retryTimes=0):
        """Write data to storage

        Before writing data, you need to specify:
            - where to write (partitions, mem)
            - type of written data
            - size of data
        For that need to use Bulk command 'download'
        """
        checksum = self._amlsChecksum(data)
        cfg = self.dev.get_active_configuration()
        intf = cfg[(0, 0)]

        epout = usb.util.find_descriptor(intf,
                                         custom_match=self._endpoint_match_out)

        controlData = pack('<IIIIHH', retryTimes, len(data), seq, checksum,
                           WRITE_MEDIA_CHEKSUM_ALG_ADDSUM, ackLen)
        controlData = controlData.ljust(0x20, b'\x00')

        self.dev.ctrl_transfer(bmRequestType=0x40,
                               bRequest=REQ_WRITE_MEDIA,
                               wValue=1,
                               wIndex=0xffff,
                               data_or_wLength=controlData)

        nbytes = epout.write(data, 1000)
        return nbytes == len(data)

    def devRead(self, size, timeout=None):
        """Read answer from USB"""
        return self.dev.read(usb.util.ENDPOINT_IN | 1, size, timeout=timeout)

    def bulkCmd(self, command, read_status=True, timeout=None):
        """Send a textual command

        When talking to U-Boot's implementation of this protocol, execute the
        given string as a U-Boot command. Not supported by other
        implementations, including the ROM one, to my knowledge.
        """
        request_type = usb.util.build_request_type(usb.util.CTRL_OUT,
                                                   usb.util.CTRL_TYPE_VENDOR,
                                                   usb.util.CTRL_RECIPIENT_DEVICE)

        terminated_cmd = command + '\0'

        # U-Boot's USB function gets confused if the string is longer than this.
        # Not sure why.
        if len(terminated_cmd) >= 128:
            raise ValueError("Bulk command must be shorter than 127 characters")

        self.dev.ctrl_transfer(bmRequestType = request_type,
                               bRequest = REQ_BULKCMD,
                               wValue = 0, # Ignored
                               wIndex = 2, # Ignored
                               data_or_wLength = command + '\0')

        if read_status:
            return self.bulkCmdStat(timeout)

    def bulkCmdStat(self, timeout=None):
        """Read bulk command status"""
        BULK_REPLY_LEN = 512
        return self.dev.read(usb.util.ENDPOINT_IN | 1, BULK_REPLY_LEN,
                             timeout=timeout)
