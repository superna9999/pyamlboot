#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0 OR MIT
# -*- coding: utf-8 -*-
"""
Amlogic Burning Image manipulation Library

   Copyright (c) 2024, SaluteDevices
   Copyright (c) 2024, JetHome

@author: Martin Kurbanov <mmkurbanov@salutedevices.com>
@author: Viacheslav Bocharov <adeep@lexina.in>
"""

import hashlib
import io
import os
import sys
from ctypes import (LittleEndianStructure, c_byte, c_char, c_uint16, c_uint32,
                    c_uint64, sizeof)


class AmlImgVersionHead(LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ('crc', c_uint32),
        ('version', c_uint32),
    ]


class AmlImgHead(LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ('vh', AmlImgVersionHead),
        ('magic', c_uint32),
        ('size', c_uint64),
        ('item_align_size', c_uint32),
        ('item_num', c_uint32),
        ('reserve', c_byte * 36),
    ]


class AmlImgItemInfo(LittleEndianStructure):
    pass


class AmlImgItemInfoV1(AmlImgItemInfo):
    _pack_ = 1
    _fields_ = [
        ('id', c_uint32),
        ('file_type', c_uint32),
        ('cur_offset', c_uint64),
        ('offset_in_img', c_uint64),
        ('size', c_uint64),
        ('main_type', c_char * 32),
        ('sub_type', c_char * 32),
        ('verify', c_uint32),
        ('is_backup', c_uint16),
        ('backup_id', c_uint16),
        ('reserve', c_byte * 24),
    ]


class AmlImgItemInfoV2(AmlImgItemInfo):
    _pack_ = 1
    _fields_ = [
        ('id', c_uint32),
        ('file_type', c_uint32),
        ('cur_offset', c_uint64),
        ('offset_in_img', c_uint64),
        ('size', c_uint64),
        ('main_type', c_char * 256),
        ('sub_type', c_char * 256),
        ('verify', c_uint32),
        ('is_backup', c_uint16),
        ('backup_id', c_uint16),
        ('reserve', c_byte * 24),
    ]


class AmlImageItem:
    def __init__(self, f, info: AmlImgItemInfo):
        self._f = f
        self._info = info
        self._main_type = info.main_type.decode('utf-8')
        self._sub_type = info.sub_type.decode('utf-8')

    def read(self, size=-1):
        offset = self.tell()
        if size == -1 or (offset + size) > self.size():
            size = self.size() - offset

        self._f.seek(self._info.offset_in_img + self._info.cur_offset)
        ret = self._f.read(size)
        self._info.cur_offset += size

        return ret

    def seek(self, pos, whence=0):
        if whence == 0:
            if pos < 0:
                raise ValueError(f'negative seek position {pos}')
            offset = pos
        elif whence == 1:
            offset = max(0, self._info.cur_offset + pos)
        elif whence == 2:
            offset = max(0, self._info.size + pos)
        else:
            raise ValueError('unsupported whence value')

        if offset > self.size():
            offset = self.size()

        self._info.cur_offset = offset
        return offset

    def tell(self):
        return self._info.cur_offset

    def size(self):
        return self._info.size

    def file_type(self):
        file_types = {
            0x00: 'normal',
            0xfe: 'sparse',
        }

        return file_types[self._info.file_type]

    def main_type(self):
        return self._main_type

    def sub_type(self):
        return self._sub_type

    def is_verify(self):
        return bool(self._info.verify)


class AmlImagePack:
    def __init__(self, name, is_cfg=False):
        self._iscfg = False
        if is_cfg:
            self._opendir(name)
        else:
            self._open(name)

    @staticmethod
    def _check_head(head):
        if head.magic != 0x27B51956:
            raise ValueError('The magic number is not match')

    @staticmethod
    def check(img):
        if isinstance(img, str):
            img_name = img
        else:
            img_name = img.name

        with open(img_name, 'rb') as f:
            head = AmlImgHead()
            read = f.readinto(head)
            assert read == sizeof(head)

            AmlImagePack._check_head(head)

    def _open(self, img):
        if isinstance(img, str):
            img_name = img
        else:
            img_name = img.name

        self._head = AmlImgHead()
        f = open(img_name, 'rb')
        read = f.readinto(self._head)
        assert read == sizeof(self._head)
        self._check_head(self._head)

        version = self._head.vh.version

        if version == 1:
            item_info_v = AmlImgItemInfoV1
        elif version == 2:
            item_info_v = AmlImgItemInfoV2
        else:
            raise NotImplementedError(f'Unknown version {version}')

        self._items = []
        for i in range(self._head.item_num):
            item = item_info_v()
            read = f.readinto(item)
            assert read == sizeof(item)
            self._items.append(AmlImageItem(f, item))

        self._f = f

    def _opendir(self, imgcfg):
        if isinstance(imgcfg, str):
            img_name = imgcfg
        else:
            img_name = imgcfg.name

        self._head = AmlImgHead()
        self._items = []

        current_section = None
        base_path = os.path.dirname(img_name)

        file = open(img_name, 'r')
        _id = 0
        for line in file:
            line = line.strip()
            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1]
            elif line.startswith('file='):
                parts = line.split()
                attributes = {}
                for part in parts:
                    key, value = part.split('=')
                    attributes[key] = value.strip('"')

                file_name = attributes['file']
                full_file_path = os.path.join(base_path, file_name)
                file_size = os.path.getsize(full_file_path) if os.path.exists(full_file_path) else 0

                info = AmlImgItemInfoV2(
                    id=0,  # Assuming 'id' and other attributes as 0 or default values for now
                    file_type=0x00 if attributes['file_type'] == 'normal' else 0xfe,
                    cur_offset=0,
                    offset_in_img=0,
                    size=file_size,
                    main_type=attributes['main_type'].encode('utf-8'),
                    sub_type=attributes['sub_type'].encode('utf-8'),
                    verify=1 if current_section == 'LIST_VERIFY' else 0,
                    is_backup=0,
                    backup_id=0,
                    reserve=(c_byte * 24)()
                )
                _id += 1

                f = open(full_file_path, "rb")
                newitem = AmlImageItem(f, info)
                self._items.append(newitem)
                if info.verify:
                    info_verify = AmlImgItemInfoV2(
                        id=0,  # Assuming 'id' and other attributes as 0 or default values for now
                        file_type=0x00 if attributes['file_type'] == 'normal' else 0xfe,
                        cur_offset=0,
                        offset_in_img=0,
                        size=file_size,
                        main_type='VERIFY'.encode('utf-8'),
                        sub_type=attributes['sub_type'].encode('utf-8'),
                        verify=0,
                        is_backup=0,
                        backup_id=0,
                        reserve=(c_byte * 24)()
                    )
                    sha1 = hashlib.sha1()
                    while True:
                        data = f.read(4096)
                        if not data:
                            break
                        sha1.update(data)
                    sha1sum = sha1.hexdigest()
                    sha_text = f'sha1sum {sha1sum}'
                    # temp_file = io.StringIO()
                    temp_file = io.BytesIO(sha_text.encode('utf-8'))
                    temp_file.name = f.name
                    f.seek(0)
                    _id += 1
                    newitem = AmlImageItem(temp_file, info_verify)
                    self._items.append(newitem)

        self._iscfg = True
        self._f = file
        return self._items

    @staticmethod
    def item_cmp(item, main_type=None, sub_type=None, file_type=None):
        if main_type and main_type != item.main_type():
            return False
        if sub_type and sub_type != item.sub_type():
            return False
        if file_type and file_type != item.file_type():
            return False
        return True

    def items(self, main_type=None, sub_type=None, file_type=None):
        return filter(
            lambda x: self.item_cmp(x, main_type, sub_type, file_type),
            self._items)

    def item_count(self, main_type=None):
        if not main_type:
            return len(self._items)

        items = filter(lambda x: self.item_cmp(x, main_type), self._items)
        return sum(1 for _ in items)

    def item_get(self, main_type, sub_type):
        flt = filter(lambda x: self.item_cmp(x, main_type, sub_type),
                     self._items)
        item = next(flt, None)
        if not item:
            raise ValueError(f'Item {main_type}:{sub_type} not found')

        return item

