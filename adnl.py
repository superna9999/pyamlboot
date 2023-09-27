#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0 OR MIT
# -*- coding: utf-8 -*-

__license__ = "GPL-2.0"
__author__ = "Arseniy Krasnov"
__email__ = "avkrasnov@salutedevices.com"
__copyright__ = "Copyright (c) 2024, SaluteDevices"
__version__ = '0.0.1'

import logging
import time

import usb.core
import usb.util

ADNL_REPLY_OKAY = 'OKAY'
ADNL_REPLY_FAIL = 'FAIL'
ADNL_REPLY_INFO = 'INFO'
ADNL_REPLY_DATA = 'DATA'

USB_IO_TIMEOUT_MS = 5000
USB_BULK_SIZE = 16384
USB_READ_LEN = 512

AMLOGIC_VENDOR_ID = 0x1b8e
AMLOGIC_PRODUCT_ID = 0xc004

BOOTROM_BURNSTEPS_0 = 0xC0040000
BOOTROM_BURNSTEPS_1 = 0xC0040001
BOOTROM_BURNSTEPS_2 = 0xC0040002
BOOTROM_BURNSTEPS_3 = 0xC0040003

TPL_BURNSTEPS_0 = 0xC0041030
TPL_BURNSTEPS_1 = 0xC0041031
TPL_BURNSTEPS_2 = 0xC0041032

ADNL_ROM_STAGE = 0
ADNL_TPL_STAGE = 16


class CBW:
    def __init__(self, msg) -> None:
        magic = msg[4:8].tobytes().decode()

        if magic != 'AMLC':
            raise RuntimeError('Unexpected CBW magic')

        self._seq = int.from_bytes(msg[8:12], 'little')
        self._size = int.from_bytes(msg[12:16], 'little')
        self._offs = int.from_bytes(msg[16:20], 'little')
        self._need_checksum = not int.from_bytes(msg[20:21], 'little')
        self._end = msg[21]

    def size(self):
        return self._size

    def done(self):
        return self._end

    def offset(self):
        return self._offs


def adnl_get_prefix(msg):
    return msg[:4].tobytes().decode()


def adnl_checksum(buf):
    # This checksum is used to verify part of image, transmitted by
    # USB. It is not for verifying entire partition image.
    return sum(int.from_bytes(buf[i:i + 4], 'little')
               for i in range(0, len(buf), 4)) & 0xffffffff


def send_cmd(epout, epin, cmd, expected_res=ADNL_REPLY_OKAY):
    epout.write(cmd, USB_IO_TIMEOUT_MS)
    msg = epin.read(USB_READ_LEN, USB_IO_TIMEOUT_MS)

    if len(msg) < 4:
        raise RuntimeError(f'Too short reply: {len(msg)}')

    strmsg = adnl_get_prefix(msg)

    if strmsg != expected_res:
        raise RuntimeError(f'Unexpected reply: {strmsg}')


def send_cmd_identify(epout, epin):
    epout.write('getvar:identify', USB_IO_TIMEOUT_MS)
    msg = epin.read(USB_READ_LEN, USB_IO_TIMEOUT_MS)
    strmsg = adnl_get_prefix(msg)

    if strmsg != ADNL_REPLY_OKAY:
        raise RuntimeError(f'Unexpected reply to "identify": {strmsg}')

    # extra checks for this type of command
    if msg[4] != 0x5:
        raise RuntimeError('Unexpected data in reply to "identify"')

    return msg[7]


def send_burnsteps(epout, epin, burnstep):
    send_cmd(epout, epin, 'setvar:burnsteps', ADNL_REPLY_DATA)

    # 'burnsteps' needs extra argument
    epout.write(burnstep.to_bytes(4, 'little'), USB_IO_TIMEOUT_MS)
    msg = epin.read(USB_READ_LEN, USB_IO_TIMEOUT_MS)
    strmsg = adnl_get_prefix(msg)

    if strmsg != ADNL_REPLY_OKAY:
        raise RuntimeError(f'Unexpected reply to "burnsteps": {strmsg}')


def tpl_burn_partition(part_item, aml_img, epout, epin):
    part_name = part_item.sub_type()
    logging.info('Burning partition "%s"', part_name)
    # To burn partition, first send the following command:
    # 'oem mwrite <partition size> normal store <partition name>'
    # Reply must be 'OKAY'.
    oem_cmd = f'oem mwrite 0x{part_item.size():x} normal store {part_name}'
    epout.write(oem_cmd, USB_IO_TIMEOUT_MS)
    msg = epin.read(USB_READ_LEN, USB_IO_TIMEOUT_MS)
    strmsg = adnl_get_prefix(msg)

    if strmsg != ADNL_REPLY_OKAY:
        raise RuntimeError(f'Unexpected reply to "oem mwrite": {strmsg}')

    while True:
        # Partition is sent step by step, each step starts from
        # command 'mwrite:verify=addsum', reply is 'DATAOUTX:Y'.
        # X is number of bytes, which device expects in this step.
        # Y is offset in the partition image. Both X and Y are in
        # hex format. If reply is 'OKAY' instead of 'DATAOUTX:Y',
        # then current step is done. After both 'X' and 'Y' are
        # received, 'X' number of bytes are sent by blocks, each
        # block is 16KB max. After 'X' bytes are transmitted,
        # control sum packet is sent. It is trimmed by 4 bytes.
        # Valid reply for checksum is 'OKAY'. Step is done, now
        # go to this step again to send rest of partition.
        # After entire parition is sent, checksum verification for
        # just transmitted partition is performed. To do this,
        # client sends 'oem verify sha1sum X', where 'X' is SHA1
        # hash for the whole parition image (currently only SHA1
        # is supported). In case of successful verification,
        # device replies 'OKAY'.

        epout.write('mwrite:verify=addsum', USB_IO_TIMEOUT_MS)
        msg = epin.read(USB_READ_LEN, USB_IO_TIMEOUT_MS)
        strmsg = msg.tobytes().decode()

        if strmsg.startswith(ADNL_REPLY_OKAY):
            logging.info('Burning is done')
            break

        if not strmsg.startswith('DATAOUT'):
            raise RuntimeError(
                f'Unexpected reply to "mwrite:verify=addsum": {strmsg}')

        size_offs = strmsg[7:].split(':')
        size = int(size_offs[0], 16)
        offs = int(size_offs[1], 16)

        part_item.seek(offs)
        buf = part_item.read(size)
        sum_res = adnl_checksum(buf)
        buf_offs = 0

        while size > 0:
            to_send = min(size, USB_BULK_SIZE)
            epout.write(buf[buf_offs:buf_offs + to_send], USB_IO_TIMEOUT_MS)
            size -= to_send
            buf_offs += to_send

        bytes_sum = [(sum_res >> i) & 0xff for i in range(0, 32, 8)]
        epout.write(bytes_sum, USB_IO_TIMEOUT_MS)
        msg = epin.read(USB_READ_LEN, USB_IO_TIMEOUT_MS)
        strmsg = adnl_get_prefix(msg)

        if strmsg != ADNL_REPLY_OKAY:
            raise RuntimeError('CRC error during tx')

    # get 'VERIFY' entry for this partition
    verify_item = aml_img.item_get('VERIFY', part_name)
    sha1sum_str = f'oem verify {verify_item.read().decode("utf-8")}'
    logging.info('Verifying partition checksum using SHA1...')
    epout.write(sha1sum_str)

    strmsg = ''

    while strmsg != ADNL_REPLY_OKAY:
        logging.info('Waiting reply...')
        msg = epin.read(USB_READ_LEN, USB_IO_TIMEOUT_MS)
        strmsg = adnl_get_prefix(msg)

        if strmsg == ADNL_REPLY_INFO:
            # Device is busy because of processing checksum
            time.sleep(1)
            continue

        if strmsg != ADNL_REPLY_OKAY:
            raise RuntimeError('CRC error for partition')

    logging.info('OK')


def send_and_handle_cbw(epout, epin):
    # CBW seems to be Control Block Word. This structure is used
    # during SPL stage. Devices requests blocks of TPL image
    # using this structure.
    logging.info('Requesting CBW...')
    epout.write('getvar:cbw', USB_IO_TIMEOUT_MS)
    msg = epin.read(USB_READ_LEN, USB_IO_TIMEOUT_MS)

    return CBW(msg)


def run_bootrom_stage(epout, epin, aml_img):
    item = aml_img.item_get('USB', 'DDR')

    logging.info('Running ROM stage...')
    # May be, sequence of commands below is not necessary,
    # but as from the device side there is closed ROM code
    # which replies to this commands, let's follow with these
    # commands as in vendor's code.
    send_cmd(epout, epin, 'getvar:serialno')
    send_cmd(epout, epin, 'getvar:getchipinfo-1')
    send_cmd(epout, epin, 'getvar:getchipinfo-0')
    send_cmd(epout, epin, 'getvar:getchipinfo-1')
    send_cmd(epout, epin, 'getvar:getchipinfo-2')
    send_cmd(epout, epin, 'getvar:getchipinfo-3')
    send_burnsteps(epout, epin, BOOTROM_BURNSTEPS_0)
    send_cmd(epout, epin, 'getvar:getchipinfo-1')
    send_burnsteps(epout, epin, BOOTROM_BURNSTEPS_1)

    # Preparing to send SPL (e.g. BL2)
    epout.write('getvar:downloadsize', USB_IO_TIMEOUT_MS)
    msg = epin.read(USB_READ_LEN, USB_IO_TIMEOUT_MS)
    strmsg = adnl_get_prefix(msg)

    if strmsg != ADNL_REPLY_OKAY:
        raise RuntimeError('Unexpected reply to "getvar:downloadsize"')

    logging.info('Send download size for BL2')
    # despite another size of image, send 00010000 as
    # param - seems ROM code works only with this value.
    send_cmd(epout, epin, 'download:00010000', ADNL_REPLY_DATA)

    logging.info('Sending SPL image...')
    send_cmd(epout, epin, item.read())
    logging.info('Done')

    send_burnsteps(epout, epin, BOOTROM_BURNSTEPS_2)

    logging.info('Send boot cmd')
    send_cmd(epout, epin, 'boot')


def run_bl2_stage(epout, epin, aml_img):
    # This stage writes to sticky register, then sends U-boot image
    # to the device and runs it. U-boot sees value in this sticky reg
    # and enters USB gadget mode to continue ADNL burning process.
    logging.info('Running BL2 stage...')

    send_cmd_identify(epout, epin)

    logging.info('Send burnsteps after BL2')
    send_burnsteps(epout, epin, BOOTROM_BURNSTEPS_3)

    item = aml_img.item_get('USB', 'UBOOT')

    while True:
        # request cbw
        cbw = send_and_handle_cbw(epout, epin)

        size = cbw.size()

        if cbw.done() != 0:
            logging.info('TPL sending is done')
            break

        item.seek(cbw.offset())
        buf = item.read(size)
        buf_offs = 0
        cur_sum = 0

        while size > 0:
            to_send = min(size, USB_BULK_SIZE)
            epout.write(f'download:{to_send:08x}',
                        USB_IO_TIMEOUT_MS)

            msg = epin.read(USB_READ_LEN, USB_IO_TIMEOUT_MS)
            strmsg = adnl_get_prefix(msg)

            if strmsg != ADNL_REPLY_DATA:
                raise RuntimeError('Unexpected reply to "download:"')

            epout.write(buf[buf_offs:buf_offs + to_send], USB_IO_TIMEOUT_MS)

            msg = epin.read(USB_READ_LEN, USB_IO_TIMEOUT_MS)
            strmsg = adnl_get_prefix(msg)

            if strmsg != ADNL_REPLY_OKAY:
                raise RuntimeError('Unexpected reply to data tx')

            cur_sum += adnl_checksum(buf[buf_offs:buf_offs + to_send])
            size -= to_send
            buf_offs += to_send

        epout.write('setvar:checksum', USB_IO_TIMEOUT_MS)
        msg = epin.read(USB_READ_LEN, USB_IO_TIMEOUT_MS)
        strmsg = adnl_get_prefix(msg)

        if strmsg != ADNL_REPLY_DATA:
            raise RuntimeError('Unexpected reply to "setvar:checksum"')

        bytes_sum = [(cur_sum >> i) & 0xff for i in range(0, 32, 8)]
        epout.write(bytes_sum, USB_IO_TIMEOUT_MS)
        msg = epin.read(USB_READ_LEN, USB_IO_TIMEOUT_MS)
        strmsg = adnl_get_prefix(msg)

        if strmsg != ADNL_REPLY_OKAY:
            raise RuntimeError('CRC error during tx')

        logging.info('Sending CRC done')


def tpl_send_burnsteps(epout, epin, second_arg):
    send_cmd(epout, epin, f'oem setvar burnsteps {hex(second_arg)}')


def get_device_eps(dev):
    cfg = dev.get_active_configuration()
    intf = cfg[(0, 0)]
    direction = usb.util.endpoint_direction
    # match the first OUT endpoint
    epout = usb.util.find_descriptor(intf, custom_match=lambda e:
                                     direction(e.bEndpointAddress) ==
                                     usb.util.ENDPOINT_OUT)
    # match the first IN endpoint
    epin = usb.util.find_descriptor(intf, custom_match=lambda e:
                                    direction(e.bEndpointAddress) ==
                                    usb.util.ENDPOINT_IN)

    return [epout, epin]


def wait_for_device(last_dev_addr):
    while True:
        dev = usb.core.find(idVendor=AMLOGIC_VENDOR_ID,
                            idProduct=AMLOGIC_PRODUCT_ID, backend=None)

        # Uboot reenables USB on the device and enters gadget mode
        # again, so wait until device appears on the USB bus with
        # another address.
        if dev is not None:
            if dev.address != last_dev_addr:
                logging.info('Device found')
                return dev

        logging.info('Waiting for the device...')
        time.sleep(1)


def run_tpl_stage(reset, erase_code, aml_img, dev_addr_rom_stage):
    # This stage runs, when Uboot is executed on the device.
    # It burns partitions (rom and spl doesn't touch storage)
    # and verifies them.
    logging.info('Running TPL stage...')

    dev = wait_for_device(dev_addr_rom_stage)

    epout, epin = get_device_eps(dev)

    logging.info('Sending identify...')

    send_cmd_identify(epout, epin)

    tpl_send_burnsteps(epout, epin, TPL_BURNSTEPS_0)
    tpl_send_burnsteps(epout, epin, TPL_BURNSTEPS_1)
    send_cmd(epout, epin, f'oem disk_initial {erase_code}')
    tpl_send_burnsteps(epout, epin, TPL_BURNSTEPS_2)

    for item in aml_img.items():
        if item.main_type() == 'PARTITION':
            tpl_burn_partition(item, aml_img, epout, epin)

    if reset:
        logging.info('Reset')
        send_cmd(epout, epin, 'reboot')


def do_adnl_burn(reset, erase_code, aml_img):
    logging.basicConfig(level=logging.INFO,
                        format='[ANDL] %(message)s')
    logging.info('Looking for USB device...')

    try:
        dev = usb.core.find(idVendor=AMLOGIC_VENDOR_ID,
                            idProduct=AMLOGIC_PRODUCT_ID, backend=None)
    except usb.core.NoBackendError:
        logging.error('Please install libusb')
        raise

    if dev is None:
        logging.info('Device not found')
        return

    dev_addr_rom_stage = dev.address

    logging.info('Setting up USB device')
    epout, epin = get_device_eps(dev)

    stage = send_cmd_identify(epout, epin)

    if stage == ADNL_TPL_STAGE:
        send_cmd(epout, epin, 'reboot-romusb')

        dev = wait_for_device(dev_addr_rom_stage)
    elif stage != ADNL_ROM_STAGE:
        raise RuntimeError(f'Unknown stage: {stage}')

    dev_addr_rom_stage = dev.address
    epout, epin = get_device_eps(dev)
    run_bootrom_stage(epout, epin, aml_img)
    run_bl2_stage(epout, epin, aml_img)
    run_tpl_stage(reset, erase_code, aml_img, dev_addr_rom_stage)

    logging.info('Done, amazing!')
