echo ##### USB Boot script !! #####
setenv bootargs console=ttyAML0,115200 earlycon
booti 0x20080000 0x26000000 0x20000000
