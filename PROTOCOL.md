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
