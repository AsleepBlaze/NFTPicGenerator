# -*- encoding: utf-8 -*-

from util.dir import ensure_dir_exists
from PIL import Image
from aid.image import ImageAid
from . import gen
from settings import image_root
import os
import os.path
from config import image_tint_config as tint_config, image_color_config as color_config
from datetime import datetime

def tint(args):
    aid = ImageAid()
    for name in os.listdir(os.path.join(image_root, args.dir)):
        if name.startswith('.'):
            continue

        if os.path.isdir(os.path.join(image_root, args.dir, name)):
            continue

        try:
            aid.tint(args.dir, name, tint_config, save_main=args.save_main, reset=args.reset)
        except Exception as e:
            print(e)

parser = gen.subs.add_parser('image:tint')
parser.set_defaults(func=tint)
parser.add_argument('dir', type=str)
parser.add_argument('--save_main', action='store_true')
parser.add_argument('--reset', action='store_true')


def color(args):
    if not args.min_area > 0:
        raise Exception('min_area')
    
    if not (args.max_colors is None or args.max_colors > 0):
        raise Exception('max_colors')

    aid = ImageAid()
    prefix = datetime.now().strftime('%Y%m%d%H%M%S')

    for name in os.listdir(os.path.join(image_root, args.dir)):
        if name.startswith('.'):
            continue

        if os.path.isdir(os.path.join(image_root, args.dir, name)):
            continue

        try:
            aid.color(args.dir, name, tint_config, color_config, prefix, args.min_area, max_colors=args.max_colors)
        except Exception as e:
            print(e)

parser = gen.subs.add_parser('image:color')
parser.set_defaults(func=color)
parser.add_argument('dir', type=str)
parser.add_argument('--min_area', type=int, default=100)
parser.add_argument('--max_colors', type=int)


def seal(args):
    cbox = args.cbox.split(':')
    
    if len(cbox) == 1:
        cbox = dict(corner=cbox[0])
    elif len(cbox) == 2:
        box = tuple(map(int, cbox[1].split(',')))
        if len(box) == 2:
            cbox = dict(corner=cbox[0], margin=box)
        elif len(box) == 4:
            cbox = dict(corner=cbox[0], margin=box[:2], size=box[-2:])
        else:
            raise Exception('bad box')
    else:
        raise Exception('bad cbox')
    
    if not cbox['corner'] in ['TL', 'TR' ,'BL', 'BR']:
        raise Exception('bad corner')

    input_path = os.path.join(image_root, args.dir)
    output_path = os.path.join(image_root, args.dir + '_sealed')
    ensure_dir_exists(output_path)
    signet = Image.open(os.path.join(image_root, args.signet))

    aid = ImageAid()
    names = os.listdir(input_path)
    for name in names:
        if name.startswith('.'):
            continue

        if os.path.isdir(os.path.join(input_path, name)):
            continue

        try:
            print('Sealing', name, '[%d/%d]' % (names.index(name) + 1, len(names)))
            aid.seal(os.path.join(input_path, name), os.path.join(output_path, name), signet, cbox=cbox)
        except Exception as e:
            print(e)

parser = gen.subs.add_parser('image:seal')
parser.set_defaults(func=seal)
parser.add_argument('dir', type=str)
parser.add_argument('signet', type=str)
parser.add_argument('--cbox', type=str, default='BR', help='TL/TR/BL/BR BR:10,10 BR:10,10,100,100')


def gif(args):
    if args.size is None:
        size = None
    else:
        size = tuple(map(int, args.size.split(',')))
        if len(size) != 2:
            raise Exception('size')

    if args.loop < 0:
        raise Exception('loop')
    
    if args.duration < 0:
        raise Exception('duration')

    aid = ImageAid()
    names = os.listdir(os.path.join(image_root, args.dir))
    for name in names:
        if name.startswith('.'):
            continue

        if not os.path.isdir(os.path.join(image_root, args.dir, name)):
            continue

        try:
            print('Making gif', name, '[%d/%d]' % (names.index(name) + 1, len(names)))
            aid.gif(args.dir, name, size=size, loop=args.loop, duration=args.duration)
        except Exception as e:
            print(e)

parser = gen.subs.add_parser('image:gif')
parser.set_defaults(func=gif)
parser.add_argument('dir', type=str)
parser.add_argument('-s', '--size', type=str, help='like: 500,500')
parser.add_argument('--loop', type=int, default=0)
parser.add_argument('--duration', type=int, default=300)


def block_info(args):
    """
    label like below:
    '2021.08.25'\
    +'\n\n'+\
    '当天第一个block hash 0xece51dfa5028a032bb0dc0dafebe9113d14e97650e51ec1f670d6cdd72d81780'\
    +'\n'+\
    '矿工 0xea674fdde714fd979de3edf0f56aa9716b898ec8'\
    +'\n'+\
    '现在的 block hash 0x69c9cd512c79e0783b5ed580bbacd21bc4e6354933e69ea6fd33755e7abf69aa'\
    +'\n'+\
    '矿工 0xea674fdde714fd979de3edf0f56aa9716b898ec8'
    """
    
    input_path = os.path.join(image_root, args.dir)
    output_path = os.path.join(image_root, args.dir + '_block_info')
    ensure_dir_exists(output_path)
    logo = Image.open(os.path.join(image_root, args.logo))

    aid = ImageAid()
    names = os.listdir(input_path)
    for name in names:
        if name.startswith('.'):
            continue

        if os.path.isdir(os.path.join(input_path, name)):
            continue

        try:
            print('Adding block info to', name, '[%d/%d]' % (names.index(name) + 1, len(names)))
            aid.block_info(
                os.path.join(input_path, name), 
                os.path.join(output_path, name), 
                logo, 
                list(map(lambda l: l.replace('\\\\', '\n'), args.label.split('\\n'))), 
                force_break=args.force_break,
                background=args.background
            )
        except Exception as e:
            print(e)

parser = gen.subs.add_parser('image:block_info')
parser.set_defaults(func=block_info)
parser.add_argument('dir', type=str)
parser.add_argument('logo', type=str)
parser.add_argument('label', type=str)
parser.add_argument('--force_break', action='store_true')
parser.add_argument('--background', action='store_true')