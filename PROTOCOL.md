# Amlogic Boot USB Protocol

## Descriptor

```
Bus 001 Device 031: ID 1b8e:c003 Amlogic, Inc. 
Device Descriptor:
  bLength                18
  bDescriptorType         1
  bcdUSB               2.00
  bDeviceClass            0 (Defined at Interface level)
  bDeviceSubClass         0 
  bDeviceProtocol         0 
  bMaxPacketSize0        64
  idVendor           0x1b8e Amlogic, Inc.
  idProduct          0xc003 
  bcdDevice            0.20
  iManufacturer           1 Amlogic
  iProduct                2 GX-CHIP
  iSerial                 0 
  bNumConfigurations      1
  Configuration Descriptor:
    bLength                 9
    bDescriptorType         2
    wTotalLength           32
    bNumInterfaces          1
    bConfigurationValue     1
    iConfiguration          0 
    bmAttributes         0x80
      (Bus Powered)
    MaxPower              500mA
    Interface Descriptor:
      bLength                 9
      bDescriptorType         4
      bInterfaceNumber        0
      bAlternateSetting       0
      bNumEndpoints           2
      bInterfaceClass       255 Vendor Specific Class
      bInterfaceSubClass      0 
      bInterfaceProtocol      0 
      iInterface              0 
      Endpoint Descriptor:
        bLength                 7
        bDescriptorType         5
        bEndpointAddress     0x81  EP 1 IN
        bmAttributes            2
          Transfer Type            Bulk
          Synch Type               None
          Usage Type               Data
        wMaxPacketSize     0x0200  1x 512 bytes
        bInterval               0
      Endpoint Descriptor:
        bLength                 7
        bDescriptorType         5
        bEndpointAddress     0x02  EP 2 OUT
        bmAttributes            2
          Transfer Type            Bulk
          Synch Type               None
          Usage Type               Data
        wMaxPacketSize     0x0200  1x 512 bytes
        bInterval               0
Device Status:     0x0000
  (Bus Powered)
```

Need to match on `1b8e:c003` VID:PID device.

## Commands

### Simple Write Memory

`AM_REQ_WRITE_MEM`

Write up to 64bytes of memory.

```
Control OUT :
bmRequestType: 0x40
bRequest: 1
wValue: 0xd900
wIndex: 0 (0x0000)
wLength: 64
```

bRequest=1

Address is encoded in wValue and wIndex :
0xd9000010 <=> wValue=0xd900 wIndex=0010

data length encodes the length to write.

### Simple Read Memory

`AM_REQ_READ_MEM`

Read up to 64bytes of memory.

```
Control IN :
bmRequestType: 0xc0
bRequest: 2
wValue: 0xd900
wIndex: 0 (0x0000)
wLength: 64
```

bRequest=2

Address is encoded in wValue and wIndex :
0xd9000010 <=> wValue=0xd900 wIndex=0010

data length encodes the length to read.

### Fill Memory

`AM_REQ_FILL_MEM`

Fill memory

```
Control OUT :
bmRequestType: 0x40
bRequest: 3
wValue: 0x0
wIndex: 0 (0x0)
wLength: Multiple of 8
```

bRequest=3

Data is a multiple of tuples of 4bytes values :
4 bytes : address (LE)
4 bytes : value (LE)

Writes `value` at `address`

### Modify Memory

`AM_REQ_MODIFY_MEM`

Modify memory

```
Control OUT :
bmRequestType: 0x40
bRequest: 4
wValue: 0x0
wIndex: 0 (0x0)
wLength: 16
```

bRequest=4

wValue is opcode :
0: write data at `mem` address
1: read/AND `mask`/write `mem` address
2: read/OR `mask`/write `mem` address
3: read/AND NOT `mask`/write `mem` address
4: read/(AND NOT `mask`) OR (`data` AND `mask`)/write `mem` address
5: read at `mem2` address and write it into `mem` address
6: read `mem2`/AND `mask`/write `mem` address
7: copy from `mem` to `mem2`, words count in `data`

Data:
4 bytes: `mem` address (LE)
4 bytes: `data` (LE)
4 bytes: `mask` (LE)
4 bytes: `mem2` address (LE)

### Run

`AM_REQ_RUN_IN_ADDR`

```
bmRequestType: 0x40
bRequest: 5
wValue: 0xd900
wIndex: 0 (0x0000)
wLength: 4
Data: 10 00 00 d9
```

bRequest=0x05

Address is encoded in wValue and wIndex :
0xd9000010 <=> wValue=0xd900 wIndex=0010

Data seems to be 4 bytes (LE) encoding the address with the first bytes ORed with 0x10.

### Write Aux

`AM_REQ_WRITE_AUX`

```
Control OUT :
bmRequestType: 0x40
bRequest: 3
wValue: 0x?
wIndex: ? (0x?)
wLength: 4
```

bRequest=6

Address is encoded in wValue and wIndex :
0xd9000010 <=> wValue=0xd900 wIndex=0010

Data encodes the value to write (LE)

TODO: How does it work

### Read Aux

`AM_REQ_READ_AUX`

```
Control OUT :
bmRequestType: 0xc0
bRequest: 7
wValue: 0xd900
wIndex: 0 (0x0000)
wLength: 64
```

bRequest=7

Address is encoded in wValue and wIndex :
0xd9000010 <=> wValue=0xd900 wIndex=0010

Returned 4 bytes is the value read  (LE)

TODO: How does it work

### Write Large Memory

`AM_REQ_WR_LARGE_MEM`

First a control OUT to start the transfer :

```
Control OUT
bmRequestType: 0x40
bRequest: 17
wValue: 0x0020
wIndex: 1 (0x0001)
wLength: 16
Data: 00 c0 00 d9 20 00 00 00 d2 69 00 00 00 00 00 00
```

bRequest=0x11

wValue is the block length
wIndex is the number of blocks
wLength is the Control data length

Data Encoding :
4 bytes of destination address (LE)
4 bytes for data size (LE)
8 bytes ??

Then BULK Out on EP 0x02 of DATA.

### Read Large Memory

`AM_REQ_RD_LARGE_MEM`

First a control OUT to start the transfer :

```
Control OUT
bmRequestType: 0x40
bRequest: 18
wValue: 0x0020
wIndex: 1 (0x0001)
wLength: 16
Data: 00 c0 00 d9 20 00 00 00 d2 69 00 00 00 00 00 00
```

bRequest=0x12

wValue is the block length
wIndex is the number of blocks
wLength is the Control data length

Data Encoding :
4 bytes of destination address (BE)
4 bytes for data size (BE)
8 bytes ??

Then BULK In on EP 0x03 of DATA.

### Identify

`AM_REQ_IDENTIFY_HOST`

```
Control IN :
bmRequestType: 0xc0
bRequest: 32
wValue: 0x0000
wIndex: 0 (0x0000)
wLength: 4 to 8
```

bRequest=0x20

### TPL

`AM_REQ_TPL_CMD`=0x30
`AM_REQ_TPL_STAT`=0x31

### Req

`AM_REQ_DOWNLOAD`=0x32
`AM_REQ_UPLOAD`=0x33
`AM_REQ_BULKCMD`=0x34

`AM_BULK_REPLY_LEN`=512

### ChipID

`ChipID` is in fact `AM_REQ_READ_MEM` at address 0x0xc8013c24

```
Control IN :
bmRequestType: 0xc0
bRequest: 2
wValue: 0xc801
wIndex: 15396 (0x3c24)
wLength: 12
```

## BL2 BOOT

```
Control OUT :
bmRequestType: 0x40
bRequest: 80
wValue: 0x0200
wIndex: 0 (0x0000)
wLength: 0
```

512bytes BULK In:
<= AMLC....
   414d4c430000000000400000000001000000000000000000…

16bytes BULK Out:
=> OKAY 0000 

[LUSB][AMLC]dataSize=16384, offset=65536, seq 0


```
Control OUT :
bmRequestType: 0x40
bRequest: 96
wValue: 0x0000
wIndex: 16383 (0x3fff)
wLength: 0
```

16384bytes BULK Out:
=> ??

16bytes BULK In:
<= OKAY 0000


```
Control OUT :
bmRequestType: 0x40
bRequest: 96
wValue: 0x0080
wIndex: 511 (0x01ff)
wLength: 0
```

512bytes BULK Out:
=> ??

16bytes BULK In:
<= OKAY 0000




```
Control OUT :
bmRequestType: 0x40
bRequest: 80
wValue: 0x0200
wIndex: 0 (0x0000)
wLength: 0
```

512bytes BULK In:
<= AMLC....
   414d4c430100000000c00000000006000000000000000000…

```
Control OUT :
bmRequestType: 0x40
bRequest: 96
wValue: 0x0000
wIndex: 49151 (0xbfff)
wLength: 0
```

16384bytes BULK Out:
=> ??

16384bytes BULK Out:
=> ??

16384bytes BULK Out:
=> ??

16bytes BULK In:
<= OKAY 0000


```
Control OUT :
bmRequestType: 0x40
bRequest: 96
wValue: 0x0300
wIndex: 511 (0x01ff)
wLength: 0
```

512bytes BULK Out:
=> ??

16bytes BULK In:
<= OKAY 0000

```
Control OUT :
bmRequestType: 0x40
bRequest: 80
wValue: 0x0200
wIndex: 0 (0x0000)
wLength: 0
```

512bytes BULK In:
<= AMLC....
   414d4c430200000000400000008003000000000000000000…

16bytes BULK Out:
=> OKAY 0000 

...
...


```
Control OUT :
bmRequestType: 0x40
bRequest: 80
wValue: 0x0200
wIndex: 0 (0x0000)
wLength: 0
```

512bytes BULK In:
<= AMLC....
   414d4c430700000070c90f00004001000001000000000000…

16bytes BULK Out:
=> OKAY 0000 

AMLC Bulk IN:
	BYTES 0-7: AMLC\0\0\0\0
	BYTES 8-11: dataSize in LE
	BYTES 12-15: offset in LE
AMLC Bulk OUT:
	BYTES 0-15: OKAY\0\0\0\0\0\0\0\0\0\0\0\0
[LUSB][AMLC]dataSize=16384, offset=65536, seq 0		=> 4000@10000
16k => 0
literally sends [65536..65536+16k] via Bulk In of multiple of 16k / 64k max
[LUSB]before wait sum
512 => 0x80	<= offset/512

	      A  M  L  S  \0 \0 \0 \0  ?? ?? ?? ?? \0 \0 \0 \0
	0000  41 4d 4c 53 00 00 00 00  70 41 be 64 00 00 00 00   AMLS.... pA.d....

	copy of [(offset + 16):(offset+512)] of last chunk

	0010  01 00 64 aa 78 56 34 12  00 00 00 00 00 00 00 00   ..d.xV4. ........
	0020  97 66 fd 3d 89 be e8 49  ae 5d 78 a1 40 60 82 13   .f.=...I .]x.@`..
	0030  00 80 06 00 00 00 00 00  70 e5 00 00 00 00 00 00   ........ p.......
	0040  00 00 00 00 00 00 00 00  47 d4 08 6d 4c fe 98 46   ........ G..mL..F
	0050  9b 95 29 50 cb bd 5a 00  70 65 07 00 00 00 00 00   ..)P..Z. pe......
	0060  00 96 02 00 00 00 00 00  00 00 00 00 00 00 00 00   ........ ........
	0070  05 d0 e1 89 53 dc 13 47  8d 2b 50 0a 4b 7a 3e 38   ....S..G .+P.Kz>8
	0080  70 fb 09 00 00 00 00 00  00 00 00 00 00 00 00 00   p....... ........
	0090  00 00 00 00 00 00 00 00  d6 d0 ee a7 fc ea d5 4b   ........ .......K
	00A0  97 82 99 34 f2 34 b6 e4  70 fb 09 00 00 00 00 00   ...4.4.. p.......
	00B0  00 0e 06 00 00 00 00 00  00 00 00 00 00 00 00 00   ........ ........
	00C0  f4 1d 14 86 cb 95 e6 11  84 88 84 2b 2b 01 ca 38   ........ ...++..8
	00D0  88 01 00 00 00 00 00 00  68 04 00 00 00 00 00 00   ........ h.......
	00E0  00 00 00 00 00 00 00 00  48 56 cc c2 cc 85 e6 11   ........ HV......
	00F0  a5 36 3c 97 0e 97 a0 ee  f0 05 00 00 00 00 00 00   .6<..... ........
	0100  68 04 00 00 00 00 00 00  00 00 00 00 00 00 00 00   h....... ........
	0110  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00   ........ ........
	0120  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00   ........ ........
	0130  00 00 00 00 00 00 00 00  34 a1 48 b8 bc 90 e6 11   ........ 4.H.....
	0140  8f ef a4 ba db 19 de 03  c0 0e 00 00 00 00 00 00   ........ ........
	0150  68 04 00 00 00 00 00 00  00 00 00 00 00 00 00 00   h....... ........
	0160  8e 59 d6 5d 5e 8b e6 11  bc b5 f0 de f1 83 72 96   .Y.]^... ......r.
	0170  28 13 00 00 00 00 00 00  68 04 00 00 00 00 00 00   (....... h.......
	0180  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00   ........ ........
	0190  00 00 10 01 00 00 00 00  00 00 00 00 00 00 00 00   ........ ........
	01A0  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00   ........ ........
	01B0  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00   ........ ........
	01C0  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00   ........ ........
	01D0  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00   ........ ........
	01E0  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00   ........ ........
	01F0  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00   ........ ........
[LUSB]check sum OKAY

[LUSB][AMLC]dataSize=49152, offset=393216, seq 1	=> 60000
48k => 0
raw data from offset to offset+datasize
512 => 0x300
???

	0000  41 4d 4c 53 01 00 00 00  e2 1b 0c dc 00 00 00 00   AMLS.... ........
	0010  94 d8 fb ff 00 00 00 00  f0 e0 fb ff 00 00 00 00   ........ ........
	0020  d4 cc fb ff 00 00 00 00  48 94 fb ff 00 00 00 00   ........ H.......
	0030  80 cb fb ff 00 00 00 00  f8 87 fb ff 00 00 00 00   ........ ........
	0040  01 1a 9e d2 e2 b7 8b 52  01 fa bf f2 02 6c a0 72   .......R .....l.r
	0050  22 00 00 b9 01 1b 9e d2  01 fa bf f2 20 00 00 b9   "....... .... ...
	0060  80 1b 9e d2 00 fa bf f2  1f 00 00 b9 00 1a 9e d2   ........ ........
	0070  00 fa bf f2 01 00 40 b9  00 1a 9e d2 21 00 0e 32   ......@. ....!..2
	0080  00 fa bf f2 01 00 00 b9  c0 03 5f d6 00 1a 9e d2   ........ .._.....
	0090  00 fa bf f2 01 00 40 b9  80 40 a0 12 21 00 00 0a   ......@. .@..!...
	00A0  00 1a 9e d2 00 fa bf f2  01 00 00 b9 c0 03 5f d6   ........ ......_.
	00B0  00 31 9e d2 00 fa bf f2  00 00 40 b9 c0 03 5f d6   .1...... ..@..._.
	00C0  01 31 9e d2 01 fa bf f2  22 00 40 b9 01 31 9e d2   .1...... ".@..1..
	00D0  01 fa bf f2 21 00 40 b9  21 00 02 4b 3f 00 00 6b   ....!.@. !..K?..k
	00E0  69 ff ff 54 c0 03 5f d6  fd 7b be a9 fd 03 00 91   i..T.._. .{......
	00F0  21 1c 00 53 f3 0b 00 f9  3f 3c 00 71 f3 03 00 aa   !..S.... ?<.q....
	0100  c8 00 00 54 60 02 40 39  80 00 00 34 73 06 00 91   ...T`.@9 ...4s...
	0110  15 29 00 94 fc ff ff 17  00 00 80 52 f3 0b 40 f9   .)...... ...R..@.
	0120  fd 7b c2 a8 c0 03 5f d6  fd 7b be a9 fd 03 00 91   .{...._. .{......
	0130  42 1c 00 53 f3 53 01 a9  5f 3c 00 71 f4 03 00 aa   B..S.S.. _<.q....
	0140  a8 01 00 54 33 10 00 51  73 01 f8 37 81 26 d3 9a   ...T3..Q s..7.&..
	0150  20 0c 00 12 1f 24 00 71  68 00 00 54 00 c0 00 11    ....$.q h..T....
	0160  02 00 00 14 00 5c 01 11  ff 28 00 94 73 12 00 51   .....\.. .(..s..Q
	0170  f6 ff ff 17 f3 53 41 a9  fd 7b c2 a8 c0 03 5f d6   .....SA. .{...._.
	0180  fd 7b bc a9 fd 03 00 91  21 1c 00 53 f3 0b 00 f9   .{...... !..S....
	0190  3f 3c 00 71 28 03 00 54  01 00 80 d2 43 01 80 d2   ?<.q(..T ....C...
	01A0  02 08 c3 9a 40 80 03 9b  24 80 00 91 00 c0 00 11   ....@... $.......
	01B0  80 68 3d 38 e0 03 02 aa  22 04 00 11 5f 7c 00 71   .h=8.... "..._|.q
	01C0  e4 87 9f 1a 1f 00 1f eb  e2 07 9f 1a 9f 00 02 6a   ........ .......j
	01D0  f3 03 01 2a 21 04 00 91  41 fe ff 54 61 7e 40 93   ...*!... A..Ta~@.
	01E0  a2 83 00 91 20 68 62 38  73 06 00 51 de 28 00 94   .... hb8 s..Q.(..
	01F0  7f 06 00 31 41 ff ff 54  f3 0b 40 f9 fd 7b c4 a8   ...1A..T ..@..{..


[LUSB][AMLC]dataSize=16384, offset=229376, seq 2	=> 38000
16k => 0
512 => 0x1c0

[LUSB][AMLC]dataSize=49152, offset=245760, seq 3	=> 3c000
48k => 0
512 => 0x1e0

[LUSB][AMLC]dataSize=49152, offset=294912, seq 4	=> 48000
48k => 0
512 => 0x240

[LUSB][AMLC]dataSize=16384, offset=65536, seq 5		=> 10000
16k => 0
512 => 0x80

[LUSB][AMLC]dataSize=1034608, offset=81920, seq 6	=> 14000
64k => 0
64k => 0x80
64k => 0x100
64k => 0x180
64k => 0x200
64k => 0x280
64k => 0x300
64k => 0x380
64k => 0x400
64k => 0x480
64k => 0x500
64k => 0x580
64k => 0x600
64k => 0x680
64k => 0x700
51568 => 0x780
512 => 0x0a0
