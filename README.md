# pyamlboot: Amlogic SoC USB Boot utility

The Amlogic SoCs have a USB Boot mode setting itself in USB Gadget mode with a custom protocol.

The protocol reverse engineering can be found in the [PROTOCOL.md|PROTOCOL.md] file.

A library `pyamlboot` provides all the calls provided by the USB protocol, and the `boot.py` permit booting from the SoC ROM in USB Boot mode.

On amlogic software release, their U-Boot version re-implements the same protocol, thus `boot.py` cannot be used in this stage, but the protocol permit running any U-Boot commands, but this is not yet implemented.

## Running U-Boot from USB Boot Mode

- Take a Libretech-CC board
- remove the SDCard & eMMC
- Connect a Serial2USB cable to the UART pins to see the boot log
- Connect a USB Type-A to Type-A cable to the top USB Connector right next to the Ethernet connector

```
Plug into this USB port
        \/
  ___   __   __
 |   | |__| |__|
 |___| |__| |__|
-----------------

``

On a Linux Machine (Windows or MacOs may also work, untested) :

```
# sudo ./boot.py libretech-cc
```

And you will see on the Host :
```
ROM: 2.2 Stage: 0.0
Writing files/libretech-cc/u-boot.bin.usb.bl2 at 0xd9000000...
[DONE]
Writing files/usbbl2runpara_ddrinit.bin at 0xd900c000...
[DONE]
Running at 0xd9000000...
[DONE]
Waiting...
[DONE]
ROM: 2.2 Stage: 0.8
Running at 0xd900c000...
[DONE]
Waiting...
[DONE]
Writing files/libretech-cc/u-boot.bin.usb.bl2 at 0xd9000000...
[DONE]
Writing files/usbbl2runpara_runfipimg.bin at 0xd900c000...
[DONE]
Writing files/libretech-cc/u-boot.bin.usb.tpl at 0x200c000...
[DONE]
Running at 0xd9000000...
[DONE]
```

And on the board UART output :
```
GXL:BL1:9ac50e:a1974b;FEAT:ADFC318C;POC:0;RCY:0;USB:0;0.0;
TE: 12921699

BL2 Built : 16:20:27, Apr 19 2018. gxl g9478cf1 - jenkins@walle02-sh

set vcck to 1120 mv
set vddee to 1000 mv
Board ID = 3
CPU clk: 1200MHz
BL2 USB 
DQS-corr enabled
DDR scramble enabled
DDR3 chl: Rank0+1 @ 912MHz
bist_test rank: 0 18 01 2f 2c 18 41 17 00 2e 33 1b 4c 17 01 2e 2a 14 41 16 00 2d 30 19 47 676  rank: 1 16 01 2c 2e 19 43 15 00 2b 32 1c 48 13 00 26 2c 14 44 15 00 2b 30 16 4a 676   - PASS

Rank0: 1024MB(auto)-2T-13

Rank1: 1024MB(auto)-2T-13
Load fip header from USB, src: 0x0000c000, des: 0x01400000, size: 0x00004000
New fip structure!
Load bl30 from USB, src: 0x00010000, des: 0x013c0000, size: 0x0000d600
Load bl31 from USB, src: 0x00020000, des: 0x05100000, size: 0x0002c600
Load bl33 from USB, src: 0x00050000, des: 0x01000000, size: 0x00079200
NOTICE:  BL3-1: v1.0(release):b60a036
NOTICE:  BL3-1: Built : 17:03:54, Apr 10 2018
[BL31]: GXL CPU setup!
NOTICE:  BL3-1: GXL normal boot!
mpu_config_enable:ok
[Image: gxl_v1.1.3308-45470c4 2018-04-12 16:22:58 jenkins@walle02-sh]
OPS=0x82
21 0b 82 00 37 6e 01 d9 a1 83 a6 c0 a5 88 58 4e 
[17.720190 Inits done]
secure task start!
high task start!
low task start!
ERROR:   Error initializing runtime service opteed_fast


U-Boot 2018.07 (Jul 27 2018 - 09:43:44 +0200) libretech-cc

DRAM:  2 GiB
MMC:   mmc@72000: 0, mmc@74000: 1
In:    serial@4c0
Out:   serial@4c0
Err:   serial@4c0
[BL31]: tee size: 0
[BL31]: tee size: 0
Net:   
Warning: ethernet@c9410000 (eth0) using random MAC address - da:0d:7d:a3:38:00
eth0: ethernet@c9410000
Hit any key to stop autoboot:  0
```