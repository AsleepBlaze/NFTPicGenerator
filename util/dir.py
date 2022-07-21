# -*- encoding: utf-8 -*-

import os

def ensure_dir_exists(path):
    try:
        os.makedirs(path)
    except os.error:
        pass