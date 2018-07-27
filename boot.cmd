echo ##### USB Boot script !! #####
setenv autoload no
dhcp
setenv serverip 10.1.2.12
setenv bootargs console=ttyAML0,115200 earlycon
tftpboot $kernel_addr_r amlogic/Image
tftpboot $fdt_addr_r $fdtfile
tftpboot $ramdisk_addr_r amlogic/rootfs.cpio.uboot
booti $kernel_addr_r $ramdisk_addr_r $fdt_addr_r
