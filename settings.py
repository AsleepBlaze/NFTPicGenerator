# -*- encoding: utf-8 -*-

import os.path

toning = dict(
    data_root   =   os.path.join(os.path.dirname(__file__), 'data', 'toning', 'data'),
    data_suffix =   '.json',
    psd_root    =   os.path.join(os.path.dirname(__file__), 'data', 'toning', 'psd')
)

assemble = dict(
    psd_root    =   os.path.join(os.path.dirname(__file__), 'data', 'assemble', 'psd')
)

image_root = os.path.join(os.path.dirname(__file__), 'data', 'image')

loot_root = os.path.join(os.path.dirname(__file__), 'data', 'loot')

font_root = os.path.join(os.path.dirname(__file__), 'font')

if os.path.exists(os.path.join(os.path.dirname(__file__), 'virtual.py')):
    __import__('virtual')