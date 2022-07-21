# -*- encoding: utf-8 -*-

import argparse

ap = argparse.ArgumentParser()
subs = ap.add_subparsers(title='commands')

import tornado.escape

def text_input(des, d=None):
    return tornado.escape.to_unicode(raw_input(des+': ')) or d

def boolean_input(des, d=True):
    i = tornado.escape.to_unicode(raw_input(des+'(yes/no): ')) or None
    if i is None:
        return d
    if not (i and i.lower() in [u'y', u'yes', u'n', u'no']):
        raise Exception('bad input')
    if i.lower() in [u'y', u'yes']:
        return True
    return False