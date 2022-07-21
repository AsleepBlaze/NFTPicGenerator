# -*- encoding: utf-8 -*-

import shutil
from aid.loot import Loot2Aid, Loot3Aid, LootAid
from util.dir import ensure_dir_exists
from . import gen
import xlrd
from settings import loot_root
import os
import json

def _import(args):
    attributes = []
    xls = xlrd.open_workbook(args.input, formatting_info=True)
    titles = ['Weapon', 'Chest', 'Head', 'Waist', 'Foot', 'Hand', 'Neck', 'Ring']
    for title in titles:
        sheet = xls.sheet_by_name(title)
        values = []
        for row in range(1, sheet.nrows):
            value = sheet.cell_value(row, 0)
            if not value in values:
                values.append(value)
        attributes.append(dict(name=title, values=values))
    for a in attributes:
        print(a['name'], len(a['values']))
    
    path = os.path.join(loot_root, args.output)
    ensure_dir_exists(os.path.dirname(path))
    with open(path, 'wb') as fo:
        fo.write(json.dumps(attributes).encode())

parser = gen.subs.add_parser('loot:import')
parser.set_defaults(func=_import)
parser.add_argument('input', type=str, help='like: /Users/cola/Downloads/LOOT_Rarity.xls')
parser.add_argument('output', type=str, default='loot.json')


def generate(args):
    size = tuple(map(int, args.size.split(',')))
    if len(size) != 2:
        raise Exception('size')
    
    aid = LootAid.load(args.name)
    if not args.sts_dir is None:
        aid.sts_dir(args.sts_dir)
    else:
        max_length = aid.max_length
        if not max_length > 0 or args.length > max_length:
            raise Exception('length %d out of max_length %d' % (args.length, max_length))
        aid.execute(size, args.padding, args.line_space, args.font_size, args.line_height, args.length)

parser = gen.subs.add_parser('loot:generate')
parser.set_defaults(func=generate)
parser.add_argument('name', type=str)
parser.add_argument('--size', type=str, default='508,508', help='like: 508,508')
parser.add_argument('--padding', type=int, default=20)
parser.add_argument('--line_space', type=int, default=5)
parser.add_argument('--font_size', type=int, default=20)
parser.add_argument('--line_height', type=int, default=28)
parser.add_argument('--length', type=int, default=1)
parser.add_argument('--sts_dir', type=str)


def generate2(args):
    aid = Loot2Aid.load(args.name)
    if not args.sts_dir is None:
        aid.sts_dir(args.sts_dir)
    elif not args.dir is None:
        output_path = os.path.join(loot_root, args.dir + '_' + os.path.splitext(args.name)[0])
        if os.path.exists(output_path):
            shutil.rmtree(output_path)
        ensure_dir_exists(output_path)
        input_path = os.path.join(loot_root, args.dir)

        def _valid(name):
            if name.startswith('.'):
                return False
            
            if os.path.isdir(os.path.join(input_path, name)):
                return False
            
            if not os.path.splitext(name)[1] in ['.png', '.jpg', '.jpeg']:
                return False
            
            return True
        
        names = list(filter(_valid, os.listdir(input_path)))
        max_length = aid.max_length
        if not max_length > 0 or len(names) > aid.max_length:
            raise Exception('count %d out of max_length %d' % (len(names), max_length))
        
        targets = []
        for name in names:
            print('Generating', name, '%d/%d' % (names.index(name) + 1, len(names)))
            targets = aid.execute(
                os.path.join(input_path, name), 
                args.padding, 
                args.line_space, 
                args.font_size, 
                args.line_height, 
                output_path, 
                targets=targets
            )
    else:
        raise Exception('bad args')

parser = gen.subs.add_parser('loot2:generate')
parser.set_defaults(func=generate2)
parser.add_argument('name', type=str)
parser.add_argument('--dir', type=str)
parser.add_argument('--padding', type=int, default=20)
parser.add_argument('--line_space', type=int, default=5)
parser.add_argument('--font_size', type=int, default=40)
parser.add_argument('--line_height', type=int, default=55)
parser.add_argument('--sts_dir', type=str)


def _import3(args):
    values = []
    with open(args.main, 'r') as fo:
        for value in fo.read().split('\n'):
            if len(value) == 0 or value in values:
                continue
            values.append(value)
    
    if len(values) == 0:
        raise Exception('0 values')
    
    prefixes = []
    if not args.prefix is None:
        with open(args.prefix, 'r') as fo:
            for value in fo.read().split('\n'):
                if len(value) == 0 or value in prefixes:
                    continue
                prefixes.append(value)
    
    suffixes = []
    if not args.suffix is None:
        with open(args.suffix, 'r') as fo:
            for value in fo.read().split('\n'):
                if len(value) == 0 or value in suffixes:
                    continue
                suffixes.append(value)
    
    if not args.input is None:
        with open(args.input, 'r') as fo:
            for line in fo.read().split('\n'):
                if len(line) == 0:
                    continue
                for value in values:
                    try:
                        index = line.index(value)
                        prefix = line[:index].strip()
                        suffix = line[(index + len(value)):].strip()
                        if len(prefix) > 0 and not prefix in prefixes:
                            prefixes.append(prefix)
                        if len(suffix) > 0 and not suffix in suffixes:
                            suffixes.append(suffix)
                        break
                    except:
                        pass
    
    attribute = dict(name=args.name, values=values)
    if len(prefixes) > 0:
        attribute['prefixes'] = prefixes
    if len(suffixes) > 0:
        attribute['suffixes'] = suffixes
    if not args.sep is None:
        attribute['sep'] = args.sep
    if not args.title is None:
        attribute['title'] = args.title
    if args.mutex:
        attribute['mutex'] = True
    
    print(
        attribute['name'], 
        len(attribute['values']), 
        'None' if attribute.get('prefixes') is None else len(attribute['prefixes']),
        'None' if attribute.get('suffixes') is None else len(attribute['suffixes'])
    )
    
    path = os.path.join(loot_root, args.output)
    if os.path.exists(path):
        with open(path, 'r') as fo:
            attributes = json.loads(fo.read())
    else:
        attributes = []
    
    _attribute = None
    for a in attributes:
        if a['name'] == attribute['name']:
            _attribute = a
            break
    
    if _attribute is None:
        attributes.append(attribute)
    else:
        attributes[attributes.index(_attribute)] = attribute
    
    ensure_dir_exists(os.path.dirname(path))
    with open(path, 'wb') as fo:
        fo.write(json.dumps(attributes).encode())

parser = gen.subs.add_parser('loot3:import')
parser.set_defaults(func=_import3)
parser.add_argument('name', type=str)
parser.add_argument('output', type=str, default='loot3.json')
parser.add_argument('main', type=str, help='like: /Users/cola/Downloads/land')
parser.add_argument('--prefix', type=str, help='like: /Users/cola/Downloads/land_prefix')
parser.add_argument('--suffix', type=str, help='like: /Users/cola/Downloads/land_suffix')
parser.add_argument('--input', type=str, help='like: /Users/cola/Downloads/ring')
parser.add_argument('--sep', type=str)
parser.add_argument('--title', type=str)
parser.add_argument('--mutex', action='store_true')


def generate3(args):
    if args.prefix_ratio < 0 or args.prefix_ratio > 1:
        raise Exception('prefix_ratio')
    
    if args.suffix_ratio < 0 or args.suffix_ratio > 1:
        raise Exception('suffix_ratio')
    
    aid = Loot3Aid.load(args.name)
    if not args.sts_dir is None:
        aid.sts_dir(args.sts_dir)
    elif not args.dir is None:
        output_path = os.path.join(loot_root, args.dir + '_' + os.path.splitext(args.name)[0])
        if os.path.exists(output_path):
            shutil.rmtree(output_path)
        ensure_dir_exists(output_path)
        input_path = os.path.join(loot_root, args.dir)

        def _valid(name):
            if name.startswith('.'):
                return False
            
            if os.path.isdir(os.path.join(input_path, name)):
                return False
            
            if not os.path.splitext(name)[1] in ['.png', '.jpg', '.jpeg']:
                return False
            
            return True
        
        names = list(filter(_valid, os.listdir(input_path)))
        max_length = aid.max_length
        if not max_length > 0 or len(names) > aid.max_length:
            raise Exception('count %d out of max_length %d' % (len(names), max_length))
        
        targets = []
        for name in names:
            print('Generating', name, '%d/%d' % (names.index(name) + 1, len(names)))
            targets = aid.execute(
                os.path.join(input_path, name), 
                args.padding, 
                args.line_space, 
                args.font_size, 
                args.line_height, 
                output_path, 
                targets=targets, 
                prefix_ratio=args.prefix_ratio, 
                suffix_ratio=args.suffix_ratio
            )
    else:
        raise Exception('bad args')

parser = gen.subs.add_parser('loot3:generate')
parser.set_defaults(func=generate3)
parser.add_argument('name', type=str)
parser.add_argument('--dir', type=str)
parser.add_argument('--padding', type=int, default=20)
parser.add_argument('--line_space', type=int, default=5)
parser.add_argument('--font_size', type=int, default=40)
parser.add_argument('--line_height', type=int, default=55)
parser.add_argument('--prefix_ratio', type=float, default=0.087)
parser.add_argument('--suffix_ratio', type=float, default=0.42)
parser.add_argument('--sts_dir', type=str)