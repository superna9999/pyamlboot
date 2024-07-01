<!--- SPDX-License-Identifier: GPL-2.0 OR MIT -->

# Description of burning firmware via the ADNL Protocol

ADNL is a new version of the firmware protocol. Unlike Optimus, in ADNL all commands are implemented through USB read/write, without additional USB requests (like `REQ_WRITE_MEM`, `REQ_TPL_CMD`).

Just like Optimus, the ADNL protocol is implemented in IPL (BootROM), SPL (BL2), and TPL (U-Boot) bootloaders.

The firmware algorithm is similar to the Optimus protocol:

1. **[IPL]** To load the new SPL into the device’s memory, first send the `download:00010000` command, followed by the file itself. The value `00010000` represents the size of the data being sent. Control is transferred to the new SPL with the `boot` command.
1. **[SPL]** Load and transfer control to the new TPL:
   1. Set the `burnsteps` variable to `0xc0040002` with the `setvar:burnsteps` command.
   1. Write the new TPL into the device's memory. The TPL is written using CBW (Control Block Word ?). CBW is a structure stored on the device that describes the data being received. CBW looks like this:
      | Offset | Name              |
      |--------|-------------------|
      | 0x00   | magic ('AMLC')    |
      | 0x04   | sequence          |
      | 0x08   | size              |
      | 0x0c   | offset            |
      | 0x10   | checksum_disabled |
      | 0x11   | done              |

      It is assumed that CBW is filled depending on burnsteps, which was set in the first step. CBW can be obtained with the getvar:cbw command. Thus, the writing algorithm looks like this:
      1. Get CBW by sending the `getvar:cbw` command.
      1. If the `done` field is not `0`, it means the new file is loaded into the device's memory.
      1. Write `size` bytes of data from the new BL2 at the `offset` from the CBW structure with the `download:<size>` command.
      1. Check the checksum of the data sent to the device by sending the `setvar:checksum` command.
      1. Go back to step 1.
   1. There is no direct command to transfer control to the new TPL. It is assumed that after the entire file is transferred, BL2 itself transfers control to it (possibly depending on `burnsteps`).
1. **[TPL]** Firmware of partitions:
   1. Send the [`oem disk_initial <erase>`](OPTIMUS.md#2-writing-partitions-to-disk).
   1. To provide information about the firmware partition, use the command: [`oem mwrite <image_size> <image_type> <media_type> <partition>`](OPTIMUS.md#2-writing-partitions-to-disk).
   1. Send the partition to the device in pieces in the following order::
      1. Send the `mwrite:verify=addsum` command.
      1. If the previous command returned the string `OKAY`, then the partition recording is successfully completed.
      1. If the previous command returned a string in the format `DATAOUT<size><offset>`, then read from the file at the `<offset>` of `<size>` bytes of data and send to the device.
      1. Read the checksum of the sent piece of data, and send the checksum (4 bytes) to the device.
      1. Go back to step 1.
   1. If necessary, check the checksum of the partition written to the device with the [`oem verify sha1sum <chksum>`](OPTIMUS.md#2-writing-partitions-to-disk).
