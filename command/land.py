# -*- encoding: utf-8 -*-

from datetime import datetime
from functools import reduce
from . import gen
import os
import json

def special_owned_parcels(args):
    with open(args.input, 'r') as fo:
        data = json.loads(fo.read())
    
    current = reduce(lambda c, i: (i if c is None and i['owner'] == args.owner.lower() else c), data, None) or dict(new=True, owner=args.owner.lower(), parcels=[])

    print('%d parcels before append' % len(current['parcels']))

    if args.min_x > args.max_x or args.min_y > args.max_y:
        raise Exception('bad range')
    
    for x in range(args.min_x, (args.max_x + 1)):
        for y in range(args.min_y, (args.max_y + 1)):
            if not reduce(lambda c, p: (p if c is None and p['x'] == x and p['y'] == y else c), current['parcels'], None) is None:
                continue
            current['parcels'].append(dict(x=x, y=y))
            print('%d,%d added' % (x, y))
    
    print('%d parcels after append' % len(current['parcels']))

    if current.get('new', False):
        del(current['new'])
        data.append(current)
    else:
        data = list(map(lambda i: (current if i['owner'] == current['owner'] else i), data))

    (name, ext) = os.path.splitext(args.input)
    output = '%s_%s%s' % (name, datetime.now().strftime('%Y%m%d%H%M%S'), ext)

    with open(output, 'wb') as fo:
        fo.write(json.dumps(data, indent=2).encode())

parser = gen.subs.add_parser('land:special_owned_parcels')
parser.set_defaults(func=special_owned_parcels)
parser.add_argument('input', type=str)
parser.add_argument('owner', type=str)
parser.add_argument('min_x', type=int)
parser.add_argument('max_x', type=int)
parser.add_argument('min_y', type=int)
parser.add_argument('max_y', type=int)