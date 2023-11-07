<!--- SPDX-License-Identifier: GPL-2.0 OR MIT -->

# Description of burning firmware via the Optimus Protocol

The Optimus protocol is implemented in several loaders:

- IPL (Initial Program Loader) - BootROM
- SPL (Secondary Program Loader) - BL2
- TPL (Tertiary Program Loader) - U-Boot

Can to determine the current loading stage by the third byte in the SoC identifier:

- IPL - 0
- SPL - 8
- TPL - 16

The firmware process can be divided into three stages:

1. Loading into the device's memory and transferring control to the new TPL.
1. Writing partitions to disk.
1. Firmware completion.

## 1. Loading into the device's memory and transferring control to the new TPL

1. **[IPL]** The device may be locked for firmware via USB. To unlock it, need to enter a password (password.bin).
   The need to enter a password is indicated by the 5th byte in the SoC identifier. The 6th byte in the SoC identifier indicates the success of the entered password:
   - 0 - the password is not correct
   - 1 - the password is correct and the device is unlocked.
1. **[IPL]** Need to determine if the device is securebooted. To do this, read the `Encrypt_reg` register from the device, as specified in the firmware configuration file.
1. **[IPL]** Write SPL (bl2) into the device's memory at the `DDRLoad` address from the configuration file using the USB request `REQ_WR_LARGE_MEM`. If the device is securebooted, need to load the encrypted SPL. After writing, transfer control to the DDRRun address using the USB request `REQ_RUN_IN_ADDR`.
1. **[SPL]** Repeat the previous step only for TPL and at the `UbootLoad` address.

## 2. Writing partitions to disk

1. **[TPL]** Send the command `disk_initial <erase>`. The parameter `<erase>` can take the following values:
   - 0 - do not erase partitions
   - 1 - erase everything except the reserved area `key`[^1]
   - 2 - forcibly erase everything except the reserved area `key`[^1]
   - 3 - erase everything, including the reserved area `key`[^1]
   - 4 - forcibly clear everything, including the reserved area `key`[^1]
1. **[TPL]** To provide information about the firmware, use the command: `download <media_type> <partition> <image_type> <image_size>`. Here are the parameters:
   - media_type - can take one of the following values:
     - store - means one of nand/emmc/spi, the bootloader will determine the type
     - nand
     - sdmmc
     - spiflash
     - key - unify key[^1]
     - mem - write to memory
   - partition - Specify the partition name
   - image_type - type of data being written. Takes one of the following values:
     - sparse
     - normal
     - ubifs
   - image_size - size of data being written
1. Write the partition using the USB request `REQ_WRITE_MEDIA`.
1. Verify that all data has arrived via USB by checking the status with the command `download get_status`.
Additionally, can verify the checksum of the flashed partition using the command `verify sha1sum <chksum>`.

[^1]: The reserved area is a special area on the nand flash for such data as `key` (unifykey), `dtb`, `bbt` (bad blocks table), `env` (U-Boot Environment). This area is located between the `bootloader` and `tpl` partitions.

## 3. Firmware completion

1. **[TPL]** Reset the environment variables to default, with the command `save_setting`.
1. **[TPL]** Complete the firmware by sending the command `burn_complete <reset>`. The parameter `<reset>` can take the following values:
   - 0 - turn off the device
   - 1 - reboot the device
   - 2 - turn off the device after pressing the power button
   - 3 - turn off the device after disconnecting the USB cable
   - 225 - returns whether the burn process is complete.
