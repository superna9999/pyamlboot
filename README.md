# pyamlboot: Amlogic SoC USB Boot utility

The Amlogic SoCs have a USB Boot mode setting itself in USB Gadget mode with a custom protocol.

The protocol reverse engineering can be found in the [PROTOCOL.md](PROTOCOL.md) file.

A library `pyamlboot` provides all the calls provided by the USB protocol, and the `boot.py` permit booting from the SoC ROM in USB Boot mode.

## S905X/S912/A113D Protocol

The GXL, GXM & GXBB uses a specific USB Boot protocol, implemented in the `boot.py` tool.

### Supported Boards

- Libretech-CC (Le Potato)

Remove the SDCard & eMMC
Connect a Serial2USB cable to the UART pins to see the boot log
Connect a USB Type-A to Type-A cable to the top USB Connector right next to the Ethernet connector

```
Plug into this USB port
        \/
  ___   __   __
 |   | |__| |__|
 |___| |__| |__|
-----------------
```

- Libretech-AC (La Frite)

Remove the eMMC & erase the SPI Flash first sectors.
Connect a Serial2USB cable to the UART pins to see the boot log
Connect a USB Type-A to Type-A cable to the top USB Connector right next to the Ethernet connector

```
Plug into this USB port
         \/
    __   __
---|  |-|  |-----
|             ::|
|             ::|
|             ::|
|             ::|

```

- Khadas VIM & VIM2 

The USB-C is used to power and communicate with the Boot ROM.

For Khadas-VIM, follow https://docs.khadas.com/vim1/HowtoBootIntoUpgradeMode.html#TST-Mode-Recommended

For Khadas-VIM2, follow https://docs.khadas.com/vim2/HowtoBootIntoUpgradeMode.html#TST-Mode-v1-4-only

### Command

```
usage: boot.py [-h] [--version] [--board-files UPATH] [--image IMAGEFILE] [--script SCRIPTFILE]
               [--fdt DTBFILE] [--ramfs RAMFSFILE]
               {khadas-vim3,q200,libretech-ac,s400,khadas-vim2,libretech-cc,khadas-vim}

USB boot tool for Amlogic

positional arguments:
  {khadas-vim3,q200,libretech-ac,s400,khadas-vim2,libretech-cc,khadas-vim}
                        board type to boot on

optional arguments:
  -h, --help            show this help message and exit
  --version, -v         show program's version number and exit
  --board-files UPATH   Path to Board files (default: None)
  --image IMAGEFILE     image file to load (default: None)
  --script SCRIPTFILE   script file to load (default: None)
  --fdt DTBFILE         dtb file to load (default: None)
  --ramfs RAMFSFILE     ramfs file to load (default: None)
```

Example from a Linux build directory:
```
sudo ./boot.py --image arch/arm64/boot/Image --fdt arch/arm64/boot/dts/amlogic/meson-gxl-s905x-libretech-cc.dtb --ramfs /path/to/rootfs.cpio.uboot --script boot.scr libretech-cc
```

Replace le board name, here `libretech-cc` by the board you want to boot.

A cpio initramfs in uboot format as `rootfs.cpio.uboot` is used in the example, can be built
using Buildroot.

Eventually change `boot.cmd` to add more commands before booting linux

If `boot.cmd` changed, run :

```
mkimage -C none -A arm -T script -d boot.cmd boot.scr
```
