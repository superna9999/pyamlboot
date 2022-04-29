<!--- SPDX-License-Identifier: GPL-2.0 OR MIT -->

# Amlogic Image Firmware (Amlogic Upgrade Package) Format

The firmware file consists of a header and an array of elements (descriptors) that describe the files stored in the firmware.
The byte order is **Little Endian**.

## Header Description

| Offset | Size (bytes) | Description                                                                             |
|--------|--------------|-----------------------------------------------------------------------------------------|
| 0x0000 | 4            | crc - checksum of the entire firmware image, excluding the first 4 bytes                |
| 0x0004 | 4            | version - currently only two versions are known, so `version` can contain `0` or `1`    |
| 0x0008 | 4            | magic - contains `0x27B51956`                                                           |
| 0x000c | 8            | size - size of the firmware image                                                       |
| 0x0014 | 4            | item align - possibly the alignment between file descriptors                            |
| 0x0018 | 4            | number of items - number of files in the firmware                                       |
| 0x001c | 36           | reserved                                                                                |

The `crc` can be calculated in Python as follows:

```python
from zlib import crc32

data = open('aml_image.img', 'rb').read()
crc = crc32(data[4:]) ^ 0xffffffff
print(hex(crc))
```

## File Descriptor

The file descriptor varies depending on the version. For version 1, it looks like this:
| Offset[^1] | Size (bytes) | Description                                                                        |
|------------|--------------|------------------------------------------------------------------------------------|
| 0x0000     | 4            | id - file identifier                                                               |
| 0x0004     | 4            | file type - type of file                                                           |
| 0x0008     | 8            | offset - the purpose of this field is unclear. It is typically set to 0             |
| 0x0010     | 8            | offset in image - absolute offset in the firmware image to the start of the file   |
| 0x0018     | 8            | size - size of the file                                                            |
| 0x0020     | 32           | main type - taken from the packing configuration file                              |
| 0x0040     | 32           | sub type - taken from the packing configuration file                               |
| 0x0060     | 4            | verify - indicates whether the checksum needs to be checked after burning          |
| 0x0064     | 2            | is backup                                                                          |
| 0x0066     | 2            | backup id                                                                          |
| 0x0068     | 24           | reserved                                                                           |

For version 2:
| Offset[^1] | Size (bytes) | Description                                                                        |
|------------|--------------|------------------------------------------------------------------------------------|
| 0x0000     | 4            | id - file identifier                                                               |
| 0x0004     | 4            | file type - type of file                                                           |
| 0x0008     | 8            | offset - the purpose of this field is unclear. It is typically set to 0            |
| 0x0010     | 8            | offset in image - absolute offset in the firmware image to the start of the file   |
| 0x0018     | 8            | size - size of the file                                                            |
| 0x0020     | 256          | main type - taken from the packing configuration file                              |
| 0x0120     | 256          | sub type - taken from the packing configuration file                               |
| 0x0220     | 4            | verify - indicates whether the checksum needs to be checked after burning          |
| 0x0224     | 2            | is backup                                                                          |
| 0x0226     | 2            | backup id                                                                          |
| 0x0228     | 24           | reserved                                                                           |

[^1]: Offset relative to the header. To get the absolute offset, add the header size (64 bytes) to `Offset`.

For version 2, the sizes for `main type` and `sub type` have been increased from 32 bytes to 256 bytes.

Currently known `file type`:
| Name   | Value |
|--------|-------|
| normal | 0x000 |
| sparse | 0x0fe |
| ubi    | 0x1fe |
| ubifs  | 0x2fe |

Currently known `main type`:

- `USB` - files (bootloader) for writing to memory
- `PARTITION` - firmware file
- `dtb` - device-tree file
- `VERIFY` - checksum file. `sub type` indicates which file it belongs to
- `conf` - configuration file for SoC (platform.conf)
