#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0 OR MIT
# -*- coding: utf-8 -*-

__license__ = "GPL-2.0"
__author__ = "Martin Kurbanov"
__email__ = "mmkurbanov@salutedevices.com"
__copyright__ = "Copyright (c) 2024, SaluteDevices"
__version__ = '0.0.1'

try:
    from pyamlboot.pyamlboot import pyamlboot
except ImportError:
    from pyamlboot import pyamlboot

import logging
import time
import typing
from collections import OrderedDict
from dataclasses import dataclass
from struct import pack, unpack

import usb_backend

USB_BACKEND = usb_backend.get_backend()


class BulkCmdError(Exception):
    pass


class TplCmdError(Exception):
    pass


class SocId:
    STAGE_MINOR_IPL = 0   # Initial Program Loader
    STAGE_MINOR_SPL = 8   # Secondary Program Loader
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


class BurnStepBase:
    def __init__(self, shared_data):
        self._shared_data = shared_data
        self._title = 'UNKNOWN'

    def _wait_device(self, for_connect=True, timeout=10.0):
        start_time = time.time()
        while True:
            try:
                pyamlboot.AmlogicSoC(usb_backend=USB_BACKEND)
            except Exception:
                if not for_connect:
                    break

                if (time.time() - start_time) >= timeout:
                    raise TimeoutError('Detect Device connect timeout')
            else:
                if for_connect:
                    break

            time.sleep(0.5)

    def header(self):
        logging.info(f'---- start {self._title} ----')

    def footer(self):
        logging.info(f'---- done {self._title} ----')

    def _check_bulk_cmd(self, cmd, status=b'success', timeout=3000):
        self._dev.bulkCmd(cmd, read_status=False, timeout=timeout)

        start_time = time.time()
        while True:
            exc = None
            try:
                response = self._dev.bulkCmdStat(timeout=timeout).tobytes()
            except Exception as e:
                exc = e
            else:
                if not response.startswith(b'Continue:34'):
                    break
                time.sleep(3)

            if int((time.time() - start_time) * 1000) > timeout:
                if not exc:
                    exc = TimeoutError()

                raise exc

        if response.rstrip(b'\x00') != status:
            raise BulkCmdError(f'Command {cmd} status failed:{response}')

    def _check_tpl_cmd(self, cmd, status=b'success'):
        self._dev.tplCommand(1, cmd)
        response = self._dev.tplStat().tobytes().rstrip(b'\x00')
        if response != status:
            raise TplCmdError(f'TPL Command status failed:{response}')


class BurnStepEraseBootloader(BurnStepBase):
    def __init__(self, shared_data, *args, **kwargs):
        super().__init__(shared_data)
        self._title = 'Erase Bootloader'

    def do(self, dev):
        self._dev = dev

        socid = SocId(self._dev.identify())
        logging.info(f'Firmware Version : {socid}')

        if socid.stage_minor == SocId.STAGE_MINOR_IPL:
            return
        elif socid.stage_minor != SocId.STAGE_MINOR_TPL:
            raise RuntimeError('Invalid power state')

        # Need this command to avoid to loose 4 bytes of commands after reset
        self._check_tpl_cmd('    echo 1234')
        self._check_bulk_cmd('    low_power')

        try:
            self._check_bulk_cmd('bootloader_is_old')
        except BulkCmdError:
            logging.info('Bootloader is new')
            return

        logging.info('Bootloader is old')
        logging.info('Erase bootloader...')

        self._check_bulk_cmd('erase_bootloader')
        try:
            self._check_bulk_cmd('reset')
        except Exception:
            pass

        logging.info('Waiting for connect device after reset...')
        self._wait_device(True)
        self._wait_device()
        logging.info('Device is connected')
        return True


class BurnStepBoardIsSecure(BurnStepBase):
    def __init__(self, shared_data, *args, **kwargs):
        super().__init__(shared_data)
        self._platform = kwargs['platform']
        self._title = 'SecureBoot check'

    def _read_encrypt_for_ipl(self):
        encrypt_reg = self._platform.Encrypt_reg
        if encrypt_reg == 0xffffffff:
            raise ValueError('Invalid encrypt register')

        enc_chip1 = self._platform.enc_chip_id1
        enc_chip2 = self._platform.enc_chip_id2

        if not encrypt_reg:
            data = self._dev.readLargeMemory(0xd9040004, 0x200)
            chipid = unpack('<I', data[:4])
            if enc_chip1 == chipid:
                encrypt_reg = self._platform.enc_reg1
            elif enc_chip2 == chipid:
                encrypt_reg = self._platform.enc_reg2

        data = self._dev.readSimpleMemory(encrypt_reg, 4)
        return encrypt_reg, unpack('<I', data[:4])[0]

    def _read_encrypt_for_tpl(self):
        encrypt_reg = self._platform.Encrypt_reg
        bulk_cmd = 'upload mem 0x{:x} normal 0x4'.format(encrypt_reg)
        self._check_bulk_cmd(bulk_cmd)
        data = self._dev.readMedia(4)
        return encrypt_reg, unpack('<I', data)[0]

    def do(self, dev):
        self._dev = dev

        socid = SocId(self._dev.identify())
        logging.info(socid)

        if socid.stage_minor == SocId.STAGE_MINOR_IPL:
            enc_reg, enc_val = self._read_encrypt_for_ipl()
        elif socid.stage_minor == SocId.STAGE_MINOR_TPL:
            enc_reg, enc_val = self._read_encrypt_for_tpl()
        else:
            enc_reg, enc_val = (0, 0)

        secure_bit = enc_val & 0x10
        logging.info(f'Read encrypt reg {enc_reg:x}:{enc_val:x} '
                     f'Secure boot bit:{secure_bit}')
        self._shared_data.set_encypt_val(enc_val)
        self._shared_data.set_secure(secure_bit != 0)


class BurnStepCheckPassword(BurnStepBase):
    def __init__(self, shared_data, *args, **kwargs):
        super().__init__(shared_data)
        self._password_fd = kwargs['password_fd']
        self._title = 'Password check'

    def do(self, dev):
        self._dev = dev
        socid = SocId(self._dev.identify())
        logging.info(socid)
        if socid.stage_minor != 0 or socid.major == 0:
            logging.info('Not support Identify 6byte!')
            return

        logging.info(f'{socid.need_password} {socid.password_ok}')
        if not socid.need_password or socid.password_ok:
            logging.info('The board is not locked')
            return

        if not self._password_fd:
            raise ValueError('The board is locked with a password! '
                             'Please provide a password')

        logging.info('Unlocking usb interface...')
        self._password_fd.seek(0, 0)
        self._dev.sendPassword(self._password_fd.read())

        time.sleep(2)
        socid = SocId(self._dev.identify())
        if not socid.password_ok:
            raise PermissionError('Check password failed')

        logging.info('Password ok')


class BurnStepDownloadBase(BurnStepBase):
    def __init__(self, shared_data, *args, **kwargs):
        super().__init__(shared_data)
        self._platform = kwargs['platform']
        self._images = kwargs['images']
        self._path = kwargs['path']
        self._part = kwargs['part']

    def _update_part(self):
        if self._shared_data.is_secure():
            self._part += '_ENC'

        self._cur_img = self._images.get((self._path, self._part))
        if not self._cur_img:
            p = '' if self._shared_data.is_secure() else 'non'
            raise ValueError(f'The image does not contain any {p}signed items')

    def _write_para(self, params):
        self._dev.writeLargeMemory(self._platform.bl2ParaAddr,
                                   params,
                                   blockLength=len(params))

    def _check_para(self, magic):
        data = self._dev.readLargeMemory(self._platform.bl2ParaAddr, 0x200)
        para_magic = unpack('<I', data[:4])[0]
        if para_magic != magic:
            raise Exception(f'Fail read para: {para_magic:x}')

        return data

    def _run_in_address(self, address):
        keep_power = False
        socid = SocId(self._dev.identify())
        socid_cmp = (socid.major,
                     socid.minor,
                     socid.stage_major,
                     socid.stage_minor)
        if socid_cmp >= (0, 9, 0, 0):
            keep_power = True

        logging.info(f'Run at {address:x}')
        self._dev.run(address, keep_power=keep_power)

    def _write_regs_do(self, ctrl_reg, ctrl_val, reg_default, val_default):
        if not ctrl_reg:
            ctrl_val = val_default
            ctrl_reg = reg_default

        ctrldata = pack('<I', ctrl_val)

        logging.info(f'Control write pll reg {ctrl_reg:08x}:{ctrl_val:08x}')
        self._dev.writeSimpleMemory(ctrl_reg, ctrldata)

    def _write_regs(self):
        control0_reg_default = 0xc110419c
        control1_reg_default = 0xc1104174
        control0_val_default = 0xb1
        control1_val_default = 0x5183
        self._write_regs_do(self._platform.Control0_reg,
                            self._platform.Control0_val,
                            control0_reg_default,
                            control0_val_default)
        time.sleep(0.5)
        self._write_regs_do(self._platform.Control1_reg,
                            self._platform.Control1_val,
                            control1_reg_default,
                            control1_val_default)
        time.sleep(0.5)

    def _download_file(self, img, address, size=0, block_length=0x1000):
        written = 0
        img.seek(0, 0)

        if not size or size > img.size():
            size = img.size()

        logging.info(
            f'Download file {img.sub_type()} ({size} bytes) at {address:x}')

        while written < size:
            buf = img.read(block_length)
            if not buf:
                break

            self._dev.writeLargeMemory(address, buf, blockLength=len(buf))
            written += block_length
            address += block_length

        assert written >= size, f'{written} >= {size}'


class BurnStepDownloadSPL(BurnStepDownloadBase):
    def __init__(self, shared_data, *args, **kwargs):
        super().__init__(shared_data, *args, **kwargs, path='USB', part='DDR')
        self._password_fd = kwargs['password_fd']
        self._title = 'Download SPL'
        if self._platform.Platform == 0x0811:
            self._params_buf = pack('<IIIIII',
                                    0x3412cdab,
                                    0x200, 0xc0df, 0, 0, 0)
        else:
            raise NotImplementedError(
                f'Platform {self._platform.Platform:x} not support')

    def do(self, dev):
        self._dev = dev

        socid = SocId(self._dev.identify())

        if socid.stage_minor == SocId.STAGE_MINOR_IPL:
            pass
        elif socid.stage_minor == SocId.STAGE_MINOR_TPL:
            return
        elif socid.stage_minor == SocId.STAGE_MINOR_SPL:
            return
        else:
            raise RuntimeError(f'Unexpected stage: {socid}')

        self._update_part()
        self._write_regs()
        self._download_file(self._cur_img,
                            self._platform.DDRLoad,
                            size=self._platform.DDRSize)
        self._write_para(self._params_buf)
        self._run_in_address(self._platform.DDRRun)

        time.sleep(8)

        socid = SocId(self._dev.identify())
        if socid.stage_minor == SocId.STAGE_MINOR_IPL:
            logging.info('CheckFileRunState succeed')
        elif socid.stage_major == 1 and socid.stage_minor == SocId.STAGE_MINOR_SPL:
            pass
        elif socid.stage_major == 0 and socid.stage_minor == SocId.STAGE_MINOR_SPL:
            if self._platform.bl2ParaAddr != 0:
                self._run_in_address(self._platform.bl2ParaAddr)
        else:
            raise RuntimeError('')

        self._check_para(0x7856efab)


class BurnStepDownloadUboot(BurnStepDownloadBase):
    def __init__(self, shared_data, *args, **kwargs):
        super().__init__(shared_data,
                         *args,
                         **kwargs,
                         path='USB',
                         part='UBOOT')
        self._title = 'Download UBOOT'

    def _run(self):
        socid = SocId(self._dev.identify())
        if socid.stage_minor == SocId.STAGE_MINOR_IPL:
            addr = self._platform.UbootRun
            self._run_in_address(addr)
        elif socid.stage_minor == SocId.STAGE_MINOR_SPL and socid.stage_major == 0:
            addr = self._platform.bl2ParaAddr
            self._run_in_address(addr)

    def _chksum(self, data):
        checksum = 0
        offset = 0
        uint32_max = (1 << 32)

        while offset < len(data):
            left = len(data) - offset
            if left >= 4:
                val = unpack('<I', data[offset:offset + 4])[0]
            elif left >= 3:
                val = unpack('<I', data[offset:offset + 4])[0] & 0xffffff
            elif left >= 2:
                val = unpack('<H', data[offset:offset + 2])[0]
            else:
                val = unpack('<B', data[offset])[0]
            offset = offset + 4
            checksum = (checksum + abs(val)) % uint32_max

        return checksum

    def _update_ddr(self):
        self._cur_img.seek(0, 0)
        chksum = self._chksum(self._cur_img.read())
        self._cur_img.seek(0, 0)

        buf = pack('<IIIIIIIII',
                   0x3412cdab, 0x200, 0xc0e0, 0, 0, 1,
                   self._platform.UbootLoad,
                   self._cur_img.size(),
                   chksum)
        buf = buf.ljust(100, b'\x00')
        self._write_para(buf)

        self._run()
        time.sleep(5)

        self._check_para(0x7856efab)
        socid = SocId(self._dev.identify())
        if socid.stage_minor == SocId.STAGE_MINOR_IPL:
            self._ddr_img.seek(0, 0)
            self._download_file(self._ddr_img,
                                self._platform.DDRLoad,
                                size=self._platform.DDRSize)

    def do(self, dev):
        self._dev = dev

        self._update_part()
        if self._shared_data.is_secure():
            self._ddr_img = self._images.get(('USB', 'DDR_ENC'))
        else:
            self._ddr_img = self._images.get(('USB', 'DDR'))

        socid = SocId(self._dev.identify())
        if socid.stage_minor == SocId.STAGE_MINOR_TPL:
            logging.info('No need download UBOOT')
            return

        if socid.stage_minor != 0 or \
                (socid.stage_major != 0 and socid.stage_minor != 8):
            raise NotImplementedError()

        self._download_file(self._cur_img, self._platform.UbootLoad)
        time.sleep(0.2)

        socid = SocId(self._dev.identify())
        if socid.stage_minor == SocId.STAGE_MINOR_IPL:
            self._download_file(self._ddr_img,
                                self._platform.DDRLoad,
                                size=self._platform.DDRSize)

        if self._platform.bl2ParaAddr:
            self._update_ddr()
            params_buf = pack('<IIIIIIIII',
                              0x3412cdab, 0x200, 0xc0e1, 0, 0, 0, 1,
                              self._platform.UbootLoad,
                              self._cur_img.size())
            self._write_para(params_buf)

        socid = SocId(self._dev.identify())
        self._run()

        self._wait_device(False)
        self._wait_device()
        time.sleep(5)

        self._dev = pyamlboot.AmlogicSoC(usb_backend=USB_BACKEND)
        socid = SocId(self._dev.identify())
        return True


class BurnStepDownloadMedia(BurnStepBase):
    def __init__(self, shared_data, *args, **kwargs):
        super().__init__(shared_data)
        self._images = kwargs['images']
        self._verify_images = kwargs['verify_images']
        self._path = kwargs['path']
        self._part = kwargs['part']
        self._title = f'Download {self._path}.{self._part}'

    def _send_download(self):
        _media_types = {
            'dtb': 'mem',
            'PARTITION': 'store',
        }

        if self._path == 'dtb':
            if self._part == 'meson1' and self._shared_data.is_secure():
                img = self._images.get((self._path, self._part + '_ENC'))
                if img and img.size() != 0:
                    self._part += '_ENC'

            cmd = '{media_type} {part_name} {img_type} {img_size}'
            part_name = 'dtb'
        else:
            part_name = self._part

        img = self._images[(self._path, self._part)]
        media_type = _media_types[self._path]
        img_type = img.file_type()

        cmd = f'download {media_type} {part_name} {img_type} {img.size()}'
        self._check_tpl_cmd(cmd)

    def _try_write_media(self, data, seq, resend_times=3):
        retry_times = 0
        ack_len = 0x200

        while True:
            success = self._dev.writeMedia(data,
                                           ackLen=ack_len,
                                           seq=seq,
                                           retryTimes=retry_times)
            if success:
                start_time = time.time()
                while True:
                    exc = None
                    try:
                        received = self._dev.devRead(ack_len, 1000).tobytes()
                    except Exception as e:
                        print(e)
                        exc = e
                    else:
                        if not received.startswith(b'Continue:32'):
                            break
                        time.sleep(3)

                    if (time.time() - start_time) > 10.0:
                        if not exc:
                            exc = TimeoutError()

                        raise exc

                if received.startswith(b'OK!!'):
                    break

            retry_times += 1
            if retry_times > resend_times:
                raise Exception()
            else:
                time.sleep(0.2)

    def _download_media(self):
        img = self._images[(self._path, self._part)]
        block_size = 0x10000
        seq = 0

        logging.info(f'Download media {self._part} {img.size()}...')

        while True:
            data = img.read(block_size)
            if not data:
                break

            self._try_write_media(data, seq)
            seq += 1

        logging.info('Transfer complete')

    def _verify_media(self, timeout=150000):
        verify_img = self._verify_images[self._part]
        args = verify_img.read().decode('utf-8').strip()
        cmd = f'verify {args}'
        logging.info(f'Verifying image {self._part}...')
        self._check_bulk_cmd(cmd, timeout=timeout)
        logging.info('Verify success')

    def do(self, dev):
        self._dev = dev

        self._send_download()
        self._download_media()
        self._check_bulk_cmd('download get_status')

        img = self._images[(self._path, self._part)]
        if img.is_verify():
            self._verify_media()


class BurnStepCommand(BurnStepBase):
    def __init__(self, shared_data, *args, **kwargs):
        super().__init__(shared_data)
        self._cmd = kwargs['cmd']
        self._title = f'Commad {self._cmd}'
        self._timeout = kwargs.get('timeout', 3000)

    def do(self, dev):
        self._dev = dev

        self._check_bulk_cmd(self._cmd, timeout=self._timeout)


class Platform:

    @dataclass
    class Parser:
        pattern: str
        fn: typing.Any
        required: bool
        defval: str

    def _cfg_parse_int(self, key, cfg_item):
        val = int(cfg_item[len(key):], 0)
        setattr(self, key[:-1], val)

    def _cfg_parse_control(self, key, cfg_item):
        reg, val = cfg_item[len(key):].split(':')
        setattr(self, key[:-1] + '_reg', int(reg, 0))
        setattr(self, key[:-1] + '_val', int(val, 0))

    def __init__(self, data):
        parsers = [
            Platform.Parser('Platform:',       self._cfg_parse_int,     True,  None),
            Platform.Parser('DDRLoad:',        self._cfg_parse_int,     True,  None),
            Platform.Parser('DDRRun:',         self._cfg_parse_int,     True,  None),
            Platform.Parser('UbootLoad:',      self._cfg_parse_int,     False, '0'),
            Platform.Parser('UbootRun:',       self._cfg_parse_int,     False, '0'),
            Platform.Parser('BinPara:',        self._cfg_parse_int,     False, '0'),
            Platform.Parser('Uboot_down:',     self._cfg_parse_int,     False, '0'),
            Platform.Parser('Uboot_decomp:',   self._cfg_parse_int,     False, '0'),
            Platform.Parser('Uboot_enc_down:', self._cfg_parse_int,     False, '0'),
            Platform.Parser('Uboot_enc_run:',  self._cfg_parse_int,     False, '0'),
            Platform.Parser('Uboot:',          self._cfg_parse_int,     False, '0'),
            Platform.Parser('Encrypt_reg:',    self._cfg_parse_int,     False, '0'),
            Platform.Parser('bl2ParaAddr=',    self._cfg_parse_int,     False, '0'),
            Platform.Parser('Control0=',       self._cfg_parse_control, True,  None),
            Platform.Parser('Control1=',       self._cfg_parse_control, True,  None),
            Platform.Parser('Encrypt_reg0=',   self._cfg_parse_int,     False, '0'),
            Platform.Parser('Encrypt_reg1=',   self._cfg_parse_int,     False, '0'),
            Platform.Parser('Encrypt_reg2=',   self._cfg_parse_int,     False, '0'),
            Platform.Parser('needPassword=',   self._cfg_parse_int,     False, '0'),
            Platform.Parser('DDRSize:',        self._cfg_parse_int,     False, '0'),
            Platform.Parser('enc_chip_id1:',   self._cfg_parse_int,     False, '0'),
            Platform.Parser('enc_chip_id2:',   self._cfg_parse_int,     False, '0'),
        ]

        for cfg_item in data.split('\n'):
            cfg_item = cfg_item.strip()
            if not cfg_item:
                continue

            parser_flt = filter(lambda x: cfg_item.startswith(x.pattern), parsers)
            parser = next(parser_flt, None)
            if parser:
                parser.fn(parser.pattern, cfg_item)
                parsers.remove(parser)
            else:
                logging.warning(f'Config value {cfg_item} not supported')

        for p in parsers:
            if p.required:
                raise ValueError(f'Required config {p.pattern} not found')

            p.fn(p.pattern, p.pattern + p.defval)


class SharedData:
    def __init__(self):
        self._progress_bar = None

    def progress(self, n=1):
        if self._progress_bar:
            self._progress_bar.update(n)

    def set_progress_bar(self, progress_bar):
        self._progress_bar = progress_bar

    def set_encypt_val(self, val):
        self._encrypt_val = val

    def set_secure(self, issecure):
        self._is_secure = bool(issecure)

    def is_secure(self):
        return self._is_secure


def do_burn(burn_steps):
    reopen_dev = True

    for step in burn_steps:
        if reopen_dev:
            try:
                dev = pyamlboot.AmlogicSoC(usb_backend=USB_BACKEND)
            except usb.core.NoBackendError:
                logging.error('Please install libusb')
                raise

        step.header()
        reopen_dev = step.do(dev)
        step.footer()

        time.sleep(0.2)


def get_burn_steps(args, shared_data, aml_img):
    bootloader_items = {
        ('USB', 'DDR'): None,
        ('USB', 'DDR_ENC'): None,
        ('USB', 'UBOOT'): None,
        ('USB', 'UBOOT_ENC'): None,
    }
    partition_items = OrderedDict()
    verify_items = {}
    platform = None

    for item in aml_img.items():
        m, t = item.main_type(), item.sub_type()
        if (m, t) in bootloader_items:
            bootloader_items[(m, t)] = item
        elif m in ('PARTITION', 'dtb'):
            partition_items[(m, t)] = item
        elif m == 'VERIFY':
            verify_items[t] = item
        elif m == 'conf' and t == 'platform':
            platform = Platform(item.read().decode())

    if not platform:
        raise RuntimeError('Platform not found')

    # TODO: support SECURE_BOOT_SET
    burn_steps = [
        BurnStepCheckPassword(shared_data, password_fd=args.password),
        BurnStepBoardIsSecure(shared_data, platform=platform),
        BurnStepDownloadSPL(shared_data,
                            images=bootloader_items,
                            platform=platform,
                            password_fd=args.password),
        BurnStepDownloadUboot(shared_data,
                              images=bootloader_items,
                              platform=platform),
        BurnStepCommand(shared_data, cmd='    low_power'),
        BurnStepCommand(shared_data,
                        cmd=f'disk_initial {args.wipe.value}',
                        timeout=60000),
    ]

    if not args.no_erase_bootloader:
        burn_steps.insert(0, BurnStepEraseBootloader(shared_data))
        burn_steps.insert(0,
                          BurnStepCheckPassword(shared_data,
                                                password_fd=args.password))

    for img in partition_items:
        if img[0] == 'dtb' and img[1] == 'meson1_ENC':
            continue

        burn_steps.append(BurnStepDownloadMedia(
            shared_data, images=partition_items,
            verify_images=verify_items, path=img[0], part=img[1]))

    if args.reset:
        reset_choice = 1  # normal reboot
    else:
        reset_choice = 3  # power off after disconnect

    burn_steps.extend([
        BurnStepCommand(shared_data, cmd='save_setting'),
        BurnStepCommand(shared_data, cmd=f'burn_complete {reset_choice}'),
    ])

    return burn_steps


def do_optimus_burn(args, aml_img):
    shared_data = SharedData()
    burn_steps = get_burn_steps(args, shared_data, aml_img)

    do_burn(burn_steps)
