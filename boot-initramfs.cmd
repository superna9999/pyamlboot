# SPDX-License-Identifier: Apache-2.0 OR MIT
setenv bootargs console=ttyAML0,115200n8 rdinit=/init
booti 0x8080000 - 0x8008000
