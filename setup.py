#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT

import setuptools

files = ["../files/*", "../files/*/*"]

setuptools.setup(name="pyamlboot",
    version="1.0.0",
    author="Neil Armstrong",
    author_email='superna9999@gmail.com',
    description="Amlogic SoC USB Boot utility",
    url='https://github.com/superna9999/pyamlboot',
    packages=['pyamlboot'],
    scripts=['boot.py', 'boot-g12.py', 'runKernel.py', 'socid.py'],
    license="Apache 2.0 OR MIT",
    install_requires=['pyusb', 'setuptools'],
    package_data = {'pyamlboot': files},
)
