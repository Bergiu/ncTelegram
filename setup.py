#!/usr/bin/env python

from distutils.core import setup

setup(name='ncTelegram',
    version='0.9.0',
    description='A curse Telegram client',
    license='GPLv3',
    author='Sébastien Lemaire',
    url='https://github.com/Nanoseb/ncTelegram',
    packages=['ncTelegram'],
    scripts=['nctelegram'],
    data_files=[('/etc', ['ncTelegram.conf']),
               ('/usr/share/ncTelegram', ['t_logo.png']),]

     )