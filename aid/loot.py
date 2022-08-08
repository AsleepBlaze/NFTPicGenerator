# -*- encoding: utf-8 -*-

from functools import reduce
from PIL import Image, ImageDraw, ImageFont
from settings import loot_root, font_root
import os
import os.path
import random
from util.dir import ensure_dir_exists
import xlwt
import json
from shutil import copyfile
import math

class LootAid:
    def __init__(self, name, attributes):
        self._name = name
        self._attributes = attributes

        print('\n### Attributes info ###')
        for a in self._attributes:
            print('%s (%d)' % (a['name'], len(a['values'])))
        print('### Attributes info ###\n')
    
    @classmethod
    def load(cls, name):
        with open(os.path.join(loot_root, name), 'r') as fo:
            return cls(os.path.splitext(name)[0], json.loads(fo.read()))
    
    @property
    def max_length(self):
        length = 0
        for a in self._attributes:
            if not len(a['values']) > 0:
                continue
            length = max(length, 1) * len(a['values'])
        return length
    
    def execute(self, size, padding, line_space, font_size, line_height, length):
        path = os.path.join(loot_root, self._name)
        ensure_dir_exists(path)

        def _new(target):
            font = ImageFont.truetype(font=os.path.join(font_root, 'EBGaramond-Regular.ttf'), size=font_size)
            im = Image.new('RGB', size, (0, 0, 0))
            draw = ImageDraw.Draw(im)
            
            lines = []
            x = 0
            y = line_space
            for a in self._attributes:
                lw, _ = draw.textsize(a['values'][target[a['name']]], font=font)
                x = max(x, lw)
                y = y + line_height + line_space
                lines.append((a['values'][target[a['name']]], line_height))
            x = padding + x + padding
            y = padding + y + padding

            w, h = im.size
            if x > w or y > h:
                scale = max(x / w, y / h)
                im = im.resize((int(w * scale), int(h * scale)))
                draw = ImageDraw.Draw(im)
            
            x = padding
            y = padding + line_space
            for (text, h) in lines:
                draw.text((x, y), text, fill='white', font=font)
                y = y + h + line_space
            
            return im
        
        for target in self._generator_random(length):
            _new(target).save(os.path.join(path, '_'.join(list(map(str, target.values()))) + '.jpg'))
    
    def _generator_random(self, length):
        targets = []
        while True:
            target = reduce(lambda target, a: dict(target, **{a['name']: random.randint(0, (len(a['values']) - 1))}) if len(a['values']) > 0 else target, self._attributes, dict())
            if target in targets:
                continue
            print(target, '%d/%d' % (len(targets) + 1, length))
            yield target
            targets.append(target)

            if len(targets) == length:
                break
    
    def _generator_reverse(self, inputs):
        els = reduce(lambda target, a: dict(target, **{a['name']: len(a['values'])}) if len(a['values']) > 0 else target, self._attributes, dict()).items()
        targets = []
        for input in inputs:
            if not len(input) == len(els):
                print('Error input %s, bad len' % input)
                continue

            els_i = list(zip(els, input))
            
            verified = True
            for ((name, length), index) in els_i:
                if index < 0 or index >= length:
                    print('Error input %s, bad index(%d) of %s' % (input, index, name))
                    verified = False
                    break
            if not verified:
                continue

            target = reduce(lambda t, el: dict(t, **{el[0][0]: el[1]}), els_i, dict())
            if target in targets:
                continue
            print(target, '%d/%d' % (inputs.index(input) + 1, len(inputs)))
            yield target
            targets.append(target)
    
    def sts_dir(self, dir):
        path = os.path.join(loot_root, dir + '_sts')
        ensure_dir_exists(path)

        def _(inputs, name):
            if name.startswith('.'):
                return inputs
            
            if os.path.isdir(os.path.join(loot_root, dir, name)):
                return inputs
            
            _origin_name, ext = tuple(os.path.splitext(name))
            id = len(inputs) + 1
            _name = '%03d' % id

            copyfile(os.path.join(loot_root, dir, name), os.path.join(path, _name + ext))
            
            return dict(inputs, **{_origin_name: dict(origin_name=(_origin_name + ext), id=id, name=('' if _name is None else (_name + ext)))})
        
        inputs = reduce(_, sorted(os.listdir(os.path.join(loot_root, dir))), dict())
        els, targets = self.sts(inputs)

        # with open(os.path.join(loot_root, dir + '_sts_els.json'), 'wb') as fo:
        #     fo.write(json.dumps(els).encode())
        
        # with open(os.path.join(loot_root, dir + '_sts_targets.json'), 'wb') as fo:
        #     fo.write(json.dumps(targets).encode())
        
        workbook = xlwt.Workbook()

        # write targets
        targets_sheet = workbook.add_sheet('Targets')
        general_names = ['origin_name', 'id', 'name']
        title = general_names + list(els.keys())

        row = 0
        for col in range(0, len(title)):
            targets_sheet.write(row, col, title[col])
        
        row = row + 1
        for target in targets:
            col = 0
            for name in title:
                targets_sheet.write(row, col, (target[name] if name in general_names else target['features'][name]))
                col = col + 1
            row = row + 1
        
        for col in range(0, len(title)):
            targets_sheet.col(col).width = 10000 if col == 0 else 10000
        # write targets

        # write els
        alignment_right = xlwt.Alignment()
        alignment_right.horz = xlwt.Alignment.HORZ_RIGHT
        style_number = xlwt.XFStyle()
        style_number.alignment = alignment_right

        for (name, el) in els.items():
            sheet = workbook.add_sheet(name)
            title = ['Name', 'Count', 'Percentage']
            sheet.write_merge(0, 0, 0, len(title) - 1, 'Total %d' % el['count'])
            row = 1
            for col in range(0, len(title)):
                sheet.write(row, col, title[col])
            
            row = row + 1
            for value in el['values']:
                sheet.write(row, 0, value['name'])
                sheet.write(row, 1, value['count'], style_number)
                sheet.write(row, 2, '%.2f%%' % (round(value['count'] / el['count'] * 100, 2) if el['count'] > 0 else 0), style_number)
                row = row + 1
            sheet.col(0).width = 15000
            sheet.col(1).width = 5000
            sheet.col(2).width = 5000
        # write els
        
        workbook.save(os.path.join(loot_root, dir + '_sts.xlsx'))
    
    def sts(self, inputs):
        els = reduce(lambda target, a: dict(target, **{a['name']: dict(values=list(map(lambda value: dict(name=value, count=0), a['values'])), count=0)}) if len(a['values']) > 0 else target, self._attributes, dict())
        targets = []
        for target in self._generator_reverse(list(map(lambda input: list(map(int, input.split('_'))), inputs.keys()))):
            _input = '_'.join(list(map(str, target.values())))
            _target = dict(origin_name=inputs[_input]['origin_name'], id=inputs[_input]['id'], name=inputs[_input]['name'], features=dict())

            for (name, index) in target.items():
                els[name]['values'][index]['count'] = els[name]['values'][index]['count'] + 1
                els[name]['count'] = els[name]['count'] + 1

                _target['features'][name] = els[name]['values'][index]['name']
            
            targets.append(_target)
        
        return els, targets


class Loot2Aid:
    def __init__(self, name, attributes):
        self._name = name
        self._attributes = attributes

        print('\n### Attributes info ###')
        for a in self._attributes:
            print('%s (%d)' % (a['name'], len(a['values'])))
        print('### Attributes info ###\n')
    
    @classmethod
    def load(cls, name):
        with open(os.path.join(loot_root, name), 'r') as fo:
            return cls(os.path.splitext(name)[0], json.loads(fo.read()))
    
    @property
    def max_length(self):
        length = 0
        for a in self._attributes:
            if not len(a['values']) > 0:
                continue
            length = max(length, 1) * len(a['values'])
        return length
    
    def execute(self, input, padding, line_space, font_size, line_height, output_path, targets=[]):
        def _new(target):
            font = ImageFont.truetype(font=os.path.join(font_root, 'EBGaramond-Regular.ttf'), size=font_size)
            im = Image.open(input)
            draw = ImageDraw.Draw(im)
            
            lines = []
            x = 0
            y = line_space
            for a in self._attributes:
                if not a['name'] in target.keys():
                    continue
                lw, _ = draw.textsize(a['values'][target[a['name']]], font=font)
                x = max(x, lw)
                y = y + line_height + line_space
                lines.append((a['values'][target[a['name']]], line_height))
            x = padding + x + padding
            y = padding + y + padding

            w, h = im.size
            if x > w or y > h:
                scale = max(x / w, y / h)
                im = im.resize((int(w * scale), int(h * scale)))
                draw = ImageDraw.Draw(im)
            
            x = padding
            y = padding + line_space
            for (text, h) in lines:
                draw.text((x, y), text, fill='white', font=font)
                y = y + h + line_space
            
            return im
        
        target = self._generator_random(targets)
        print(target)
        imgs = list(map(lambda length: _new(dict(list(target.items())[:length])), range(0, len(target) + 1)))
        imgs[0].save(
            os.path.join(output_path, '%s#%s.gif' % (os.path.splitext(os.path.basename(input))[0], '_'.join(list(map(str, target.values()))))), 
            save_all=True, 
            append_images=imgs[1:], 
            loop=0, 
            duration=list(map(lambda index: 120000 if index in [len(imgs) - 1] else 400, range(0, len(imgs))))
        )
        return targets + [target]
    
    def _generator_random(self, targets):
        while True:
            target = reduce(lambda target, a: dict(target, **{a['name']: random.randint(0, (len(a['values']) - 1))}) if len(a['values']) > 0 else target, self._attributes, dict())
            if target in targets:
                continue
            return target
    
    def _generator_reverse(self, inputs):
        els = reduce(lambda target, a: dict(target, **{a['name']: len(a['values'])}) if len(a['values']) > 0 else target, self._attributes, dict()).items()
        targets = []
        for input in inputs:
            if not len(input) == len(els):
                print('Error input %s, bad len' % input)
                continue

            els_i = list(zip(els, input))
            
            verified = True
            for ((name, length), index) in els_i:
                if index < 0 or index >= length:
                    print('Error input %s, bad index(%d) of %s' % (input, index, name))
                    verified = False
                    break
            if not verified:
                continue

            target = reduce(lambda t, el: dict(t, **{el[0][0]: el[1]}), els_i, dict())
            if target in targets:
                continue
            print(target, '%d/%d' % (inputs.index(input) + 1, len(inputs)))
            yield target
            targets.append(target)
    
    def sts_dir(self, dir):
        def _(inputs, name):
            if name.startswith('.'):
                return inputs
            
            if os.path.isdir(os.path.join(loot_root, dir, name)):
                return inputs
            
            names = name.split('#')
            if len(names) > 2:
                return inputs
            
            if len(names) == 1:
                _name = None
                _origin_name, ext = tuple(os.path.splitext(names[0]))
            else:
                _name = names[0]
                _origin_name, ext = tuple(os.path.splitext(names[1]))
            
            try:
                id = int(_name)
            except:
                id = ''
            
            return dict(inputs, **{_origin_name: dict(id=id, name=('' if _name is None else (_name + ext)))})
        
        inputs = reduce(_, sorted(os.listdir(os.path.join(loot_root, dir))), dict())
        els, targets = self.sts(inputs)

        # with open(os.path.join(loot_root, dir + '_sts_els.json'), 'wb') as fo:
        #     fo.write(json.dumps(els).encode())
        
        # with open(os.path.join(loot_root, dir + '_sts_targets.json'), 'wb') as fo:
        #     fo.write(json.dumps(targets).encode())
        
        workbook = xlwt.Workbook()

        # write targets
        targets_sheet = workbook.add_sheet('Targets')
        general_names = ['id', 'name']
        title = general_names + list(els.keys())

        row = 0
        for col in range(0, len(title)):
            targets_sheet.write(0, col, title[col])
        
        row = row + 1
        for target in targets:
            col = 0
            for name in title:
                targets_sheet.write(row, col, (target[name] if name in general_names else target['features'][name]))
                col = col + 1
            row = row + 1
        
        for col in range(0, len(title)):
            targets_sheet.col(col).width = 5000 if col == 0 else 12000
        # write targets

        # write els
        alignment_right = xlwt.Alignment()
        alignment_right.horz = xlwt.Alignment.HORZ_RIGHT
        style_number = xlwt.XFStyle()
        style_number.alignment = alignment_right

        for (name, el) in els.items():
            sheet = workbook.add_sheet(name)
            title = ['Name', 'Count', 'Percentage']
            sheet.write_merge(0, 0, 0, len(title) - 1, 'Total %d' % el['count'])
            row = 1
            for col in range(0, len(title)):
                sheet.write(row, col, title[col])
            
            row = row + 1
            for value in el['values']:
                sheet.write(row, 0, value['name'])
                sheet.write(row, 1, value['count'], style_number)
                sheet.write(row, 2, '%.2f%%' % (round(value['count'] / el['count'] * 100, 2) if el['count'] > 0 else 0), style_number)
                row = row + 1
            sheet.col(0).width = 15000
            sheet.col(1).width = 5000
            sheet.col(2).width = 5000
        # write els
        
        workbook.save(os.path.join(loot_root, dir + '_sts.xlsx'))
    
    def sts(self, inputs):
        els = reduce(lambda target, a: dict(target, **{a['name']: dict(values=list(map(lambda value: dict(name=value, count=0), a['values'])), count=0)}) if len(a['values']) > 0 else target, self._attributes, dict())
        targets = []
        for target in self._generator_reverse(list(map(lambda input: list(map(int, input.split('_'))), inputs.keys()))):
            _input = '_'.join(list(map(str, target.values())))
            _target = dict(id=inputs[_input]['id'], name=inputs[_input]['name'], features=dict())

            for (name, index) in target.items():
                els[name]['values'][index]['count'] = els[name]['values'][index]['count'] + 1
                els[name]['count'] = els[name]['count'] + 1

                _target['features'][name] = els[name]['values'][index]['name']
            
            targets.append(_target)
        
        return els, targets


class Loot3Aid:
    def __init__(self, name, attributes):
        self._name = name
        self._attributes = attributes

        print('\n### Attributes info ###')
        for a in self._attributes:
            print(
                a['name'], 
                len(a['values']), 
                'None' if a.get('prefixes') is None else len(a['prefixes']),
                'None' if a.get('suffixes') is None else len(a['suffixes'])
            )
        print('### Attributes info ###\n')
    
    @classmethod
    def load(cls, name):
        with open(os.path.join(loot_root, name), 'r') as fo:
            return cls(os.path.splitext(name)[0], json.loads(fo.read()))
    
    @property
    def max_length(self):
        length = 0
        for a in self._attributes:
            if not len(a['values']) > 0:
                continue
            length = max(length, 1) * len(a['values'])
        return length
    
    def execute(self, input, padding, line_space, font_size, line_height, output_path, targets=[], prefix_ratio=0, suffix_ratio=0):
        def _new(target):
            font = ImageFont.truetype(font=os.path.join(font_root, 'EBGaramond-Regular.ttf'), size=font_size)
            im = Image.open(input)
            draw = ImageDraw.Draw(im)
            
            lines = []
            x = 0
            y = line_space
            for a in self._attributes:
                if not a['name'] in target.keys():
                    continue
                
                _index = list(map(int, target[a['name']].split('+')))
                if not len(_index) == 3:
                    text = ''
                else:
                    text = [a['values'][_index[1]]]
                    if not _index[0] == -1:
                        text = [a['prefixes'][_index[0]]] + text
                    if not _index[2] == -1:
                        text = text + [a['suffixes'][_index[2]]]
                    text = a.get('sep', ' ').join(text)
                
                if not a.get('title') is None:
                    text = a['title'] + ': ' + text
                
                lw, _ = draw.textsize(text, font=font)
                x = max(x, lw)
                y = y + line_height + line_space
                lines.append((text, line_height))
            x = padding + x + padding
            y = padding + y + padding

            w, h = im.size
            if x > w or y > h:
                scale = max(x / w, y / h)
                im = im.resize((int(w * scale), int(h * scale)))
                draw = ImageDraw.Draw(im)
            
            x = padding
            y = padding + line_space
            for (text, h) in lines:
                draw.text((x, y), text, fill='white', font=font)
                y = y + h + line_space
            
            return im
        
        target = self._generator_random(targets, prefix_ratio=prefix_ratio, suffix_ratio=suffix_ratio)
        print(target)
        _new(target).save(os.path.join(output_path, '%s#%s%s' % (os.path.splitext(os.path.basename(input))[0], '_'.join(target.values()), os.path.splitext(os.path.basename(input))[1])))
        # imgs = list(map(lambda length: _new(dict(list(target.items())[:length])), range(0, len(target) + 1)))
        # imgs[0].save(
        #     os.path.join(output_path, '%s#%s.gif' % (os.path.splitext(os.path.basename(input))[0], '_'.join(target.values()))), 
        #     save_all=True, 
        #     append_images=imgs[1:], 
        #     loop=0, 
        #     duration=list(map(lambda index: 120000 if index in [len(imgs) - 1] else 400, range(0, len(imgs))))
        # )
        return targets + [target]
    
    def _generator_random(self, targets, prefix_ratio=0, suffix_ratio=0):
        def _find(a):
            while True:
                value = random.randint(0, (len(a['values']) - 1))
                
                if not a.get('prefixes') is None:
                    prefix = random.randint(0, (math.ceil(len(a['prefixes']) / min(1.0, prefix_ratio)) - 1)) if prefix_ratio > 0 else -1
                    prefix = prefix if prefix < len(a['prefixes']) else -1
                else:
                    prefix = -1
                
                if not a.get('suffixes') is None:
                    suffix = random.randint(0, (math.ceil(len(a['suffixes']) / min(1.0, suffix_ratio)) - 1)) if suffix_ratio > 0 else -1
                    suffix = suffix if suffix < len(a['suffixes']) else -1
                else:
                    suffix = -1
                
                if a.get('mutex') is True and (value == prefix or value == suffix or (prefix == suffix and not prefix == -1)):
                    continue
                
                return '%d+%d+%d' % (prefix, value, suffix)

        while True:
            target = reduce(lambda target, a: dict(target, **{a['name']: _find(a)}) if len(a['values']) > 0 else target, self._attributes, dict())
            if target in targets:
                continue
            return target
    
    def _generator_reverse(self, inputs):
        els = reduce(lambda target, a: dict(target, **{a['name']: '%d+%d+%d' % ((0 if a.get('prefixes') is None else len(a['prefixes'])), len(a['values']), (0 if a.get('suffixes') is None else len(a['suffixes'])))}) if len(a['values']) > 0 else target, self._attributes, dict()).items()
        targets = []
        for input in inputs:
            if not len(input) == len(els):
                print('Error input %s, bad len' % input)
                continue

            els_i = list(zip(els, input))
            
            verified = True
            for ((name, length), index) in els_i:
                _length = list(map(int, length.split('+')))
                _index = list(map(int, index.split('+')))

                if not len(_length) == len(_index):
                    print('Error index %s not match %s' % (index, length))
                    verified = False
                    break

                for (l, i) in list(zip(_length, _index)):
                    if i < -1 or i >= l:
                        print('Error input %s, bad index(%s) of %s' % (input, index, name))
                        verified = False
                        break
                
                if not verified:
                    break
            if not verified:
                continue

            target = reduce(lambda t, el: dict(t, **{el[0][0]: el[1]}), els_i, dict())
            if target in targets:
                continue
            print(target, '%d/%d' % (inputs.index(input) + 1, len(inputs)))
            yield target
            targets.append(target)
    
    def sts_dir(self, dir):
        def _(inputs, name):
            if name.startswith('.'):
                return inputs
            
            if os.path.isdir(os.path.join(loot_root, dir, name)):
                return inputs
            
            names = name.split('#')
            if len(names) > 2:
                return inputs
            
            if len(names) == 1:
                _name = None
                _origin_name, ext = tuple(os.path.splitext(names[0]))
            else:
                _name = names[0]
                _origin_name, ext = tuple(os.path.splitext(names[1]))
            
            try:
                id = int(_name)
            except:
                id = ''
            
            return dict(inputs, **{_origin_name: dict(id=id, name=('' if _name is None else (_name + ext)))})
        
        inputs = reduce(_, sorted(os.listdir(os.path.join(loot_root, dir))), dict())
        els, targets = self.sts(inputs)

        # with open(os.path.join(loot_root, dir + '_sts_els.json'), 'wb') as fo:
        #     fo.write(json.dumps(els).encode())
        
        # with open(os.path.join(loot_root, dir + '_sts_targets.json'), 'wb') as fo:
        #     fo.write(json.dumps(targets).encode())
        
        workbook = xlwt.Workbook()

        # write targets
        targets_sheet = workbook.add_sheet('Targets')
        general_names = ['id', 'name']
        title = general_names + list(els.keys())

        row = 0
        for col in range(0, len(title)):
            targets_sheet.write(0, col, title[col])
        
        row = row + 1
        for target in targets:
            col = 0
            for name in title:
                targets_sheet.write(row, col, (target[name] if name in general_names else target['features'][name]))
                col = col + 1
            row = row + 1
        
        for col in range(0, len(title)):
            targets_sheet.col(col).width = 5000 if col == 0 else 12000
        # write targets

        # write els
        alignment_right = xlwt.Alignment()
        alignment_right.horz = xlwt.Alignment.HORZ_RIGHT
        style_number = xlwt.XFStyle()
        style_number.alignment = alignment_right

        for (name, el) in els.items():
            sheet = workbook.add_sheet(name)
            title = ['Name', 'Count', 'Percentage']
            sheet.write_merge(0, 0, 0, len(title) - 1, 'Total %d' % el['count'])
            row = 1
            for col in range(0, len(title)):
                sheet.write(row, col, title[col])
            
            row = row + 1
            for value in sorted(list(el['values'].values()), key=lambda v: v['count'], reverse=True):
                sheet.write(row, 0, value['name'])
                sheet.write(row, 1, value['count'], style_number)
                sheet.write(row, 2, '%.2f%%' % (round(value['count'] / el['count'] * 100, 2) if el['count'] > 0 else 0), style_number)
                row = row + 1
            sheet.col(0).width = 15000
            sheet.col(1).width = 5000
            sheet.col(2).width = 5000
        # write els
        
        workbook.save(os.path.join(loot_root, dir + '_sts.xlsx'))
    
    def sts(self, inputs):
        def _name(a, index):
            _index = list(map(int, index.split('+')))
            if not len(_index) == 3:
                text = ''
            else:
                text = [a['values'][_index[1]]]
                if not _index[0] == -1:
                    text = [a['prefixes'][_index[0]]] + text
                if not _index[2] == -1:
                    text = text + [a['suffixes'][_index[2]]]
                text = a.get('sep', ' ').join(text)
            return text
        
        els = reduce(lambda target, a: dict(target, **{a['name']: dict(values=dict(), count=0, data=a)}) if len(a['values']) > 0 else target, self._attributes, dict())
        targets = []
        for target in self._generator_reverse(list(map(lambda input: input.split('_'), inputs.keys()))):
            _input = '_'.join(target.values())
            _target = dict(id=inputs[_input]['id'], name=inputs[_input]['name'], features=dict())

            for (name, index) in target.items():
                value = dict(name=_name(els[name]['data'], index), count=0) if els[name]['values'].get(index) is None else els[name]['values'][index]
                
                value['count'] = value['count'] + 1
                els[name]['count'] = els[name]['count'] + 1

                _target['features'][name] = value['name']

                els[name]['values'][index] = value
            
            targets.append(_target)
        
        return els, targets