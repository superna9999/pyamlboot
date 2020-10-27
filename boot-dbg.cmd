echo ##### USB Boot script !! #####
setenv bootargs console=ttyAML0,115200 drm.debug=0x3f debug earlycon
booti 0x8080000 0x13000000 0x8008000
