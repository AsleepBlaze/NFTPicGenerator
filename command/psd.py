# -*- encoding: utf-8 -*-

from aid.assemble import AssembleAid
from aid.toning import ToningAid
from . import gen

def toning(args):
    # aid = ToningAid(dict(
    #     name='001',
    #     psd='001.psd',
    #     layers={
    #         'kuzi': {
    #             'from': [[{'kind': 'eq', 'value': 196}, {'kind': 'eq', 'value': 226}, {'kind': 'eq', 'value': 234}]],
    #             'to': [
    #                 [[255, 0, 0]],
    #                 [[255, 255, 0]],
    #             ]
    #         },
    #         'yifu': {
    #             'from': [[{'kind': 'gte', 'value': 173}, {'kind': 'gte', 'value': 191}, {'kind': 'gte', 'value': 86}]],
    #             'to': [
    #                 [[0, 255, 255]],
    #                 [[0, 0, 255]],
    #             ]
    #         },
    #         'toufa': {
    #             'from': [[{'kind': 'range', 'value': [1, 254]}, {'kind': 'range', 'value': [1, 254]}, {'kind': 'range', 'value': [1, 254]}]],
    #             'to': [
    #                 [[0, 255, 0]],
    #                 [[255, 0, 255]],
    #                 [[255, 255, 255]]
    #             ]
    #         }
    #     },
    #     exclusions=[
    #         {'kuzi': 0, 'yifu': 1},
    #         {'kuzi': 1, 'toufa': 0}
    #     ]
    # ))
    aid = ToningAid.load('001')
    aid.save()
    aid.execute()

parser = gen.subs.add_parser('psd:toning')
parser.set_defaults(func=toning)


def assemble(args):
    if args.size is None:
        size = None
    else:
        size = tuple(map(int, args.size.split(',')))
        if len(size) != 2:
            raise Exception('size')
    
    if args.preview_config is None:
        preview_config = None
    else:
        (column, width, height) = tuple(map(int, args.preview_config.split(',')))
        preview_config = dict(column=column, thumb_size=(width, height))
    
    aid = AssembleAid.load(args.names.split(','), config=args.config)
    if not args.sts_dir is None:
        aid.sts_dir(args.sts_dir)
    elif args.sts:
        aid.sts_all()
    elif not args.inputs_dir is None:
        aid.execute(inputs_dir=args.inputs_dir, use_jpg=args.use_jpg)
    else:
        max_length = aid.max_length
        if not max_length > 0 or args.length > max_length:
            raise Exception('length %d out of max_length %d' % (args.length, max_length))
        aid.execute(size=size, length=args.length, preview_config=preview_config, use_jpg=args.use_jpg)

parser = gen.subs.add_parser('psd:assemble')
parser.set_defaults(func=assemble)
parser.add_argument('names', type=str)
parser.add_argument('-s', '--size', type=str, help='like: 500,500')
parser.add_argument('-l', '--length', type=int, default=1)
parser.add_argument('--config', type=str, help='like: config.json')
parser.add_argument('--preview_config', type=str, help='like: 10,300,300')
parser.add_argument('--use_jpg', action='store_true')
parser.add_argument('--sts', action='store_true')
parser.add_argument('--sts_dir', type=str)
parser.add_argument('--inputs_dir', type=str)


from settings import assemble as settings
import random
import os
import shutil

def rename(args):
    padding = 0 if args.padding is None else args.padding
    if padding < 0:
        raise Exception('bad padding %d' % padding)

    def _valid(name):
        if name.startswith('.'):
            return False
        
        if os.path.isdir(os.path.join(settings['psd_root'], args.dir, name)):
            return False
        
        if not os.path.splitext(name)[1] in ['.png', '.jpg', '.jpeg', '.gif']:
            return False
        
        return True
    
    names = list(filter(_valid, os.listdir(os.path.join(settings['psd_root'], args.dir))))
    index = 1
    while len(names) > 0:
        name = names[random.randint(0, (len(names) - 1))]
        to_name = ('%%0%dd' % args.length) % (padding + index) + '#' + name
        print('move %s to %s' % (name, to_name))
        shutil.move(
            os.path.join(settings['psd_root'], args.dir, name), 
            os.path.join(settings['psd_root'], args.dir, to_name)
        )
        names.remove(name)
        index = index + 1
        
parser = gen.subs.add_parser('psd:assembled:rename')
parser.set_defaults(func=rename)
parser.add_argument('dir', type=str)
parser.add_argument('length', type=int)
parser.add_argument('--padding', type=int)


from util.dir import ensure_dir_exists
import json

def parse_exclusions(args):
    values = []
    with open(args.input, 'r') as fo:
        for value in fo.read().split('\n'):
            if len(value) == 0:
                continue
            print('Parsing', value)
            abs = value.split('Not')
            if not len(abs) == 2:
                print('bad line %s' % value)
                continue
            a = abs[0].strip()
            bs = list(map(lambda b: b.strip(), abs[1].split(',')))
            if not len(a) > 0 or not len(bs) > 0 or not len(list(filter(lambda b: len(b) > 0, bs))) == len(bs):
                print('bad line %s' % value)
                continue
            
            for b in bs:
                values.append({args.key_a: a, args.key_b: b})
                print(values[-1])
    
    if len(values) == 0:
        raise Exception('0 values')
    
    if os.path.exists(args.output):
        with open(args.output, 'r') as fo:
            config = json.loads(fo.read())
    else:
        config = dict()
    
    config['exclusions'] = config.get('exclusions', []) + values

    ensure_dir_exists(os.path.dirname(args.output))
    with open(args.output, 'wb') as fo:
        fo.write(json.dumps(config).encode())

parser = gen.subs.add_parser('psd:exclusion:parse')
parser.set_defaults(func=parse_exclusions)
parser.add_argument('input', type=str)
parser.add_argument('output', type=str)
parser.add_argument('key_a', type=str)
parser.add_argument('key_b', type=str)