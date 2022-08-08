# -*- encoding: utf-8 -*-

from functools import reduce
import json
from PIL import Image, ImageDraw, ImageFont
from psd_tools import PSDImage
from psd_tools.api.numpy_io import has_transparency
from psd_tools.api.pil_io import _apply_icc
from psd_tools.constants import Resource
from settings import assemble as settings, font_root
import os
import os.path
import random
from util.dir import ensure_dir_exists
from datetime import datetime
import math
import xlwt

class AssembleAid:
    def __init__(self, name, psds, config=None):
        self._name = name
        self._psds = psds
        self._config = config

        print('\n### PSD info ###')
        for psd in self._psds:
            print('\n%s' % psd)
            for layer in psd:
                print('\n%s' % layer, layer.offset, layer.size)
                if layer.is_group():
                    for child in layer:
                        print(child, child.offset, child.size)
            print('')
        print('### PSD info ###\n')

        if isinstance(self._config, dict) and isinstance(self._config.get('exclusions'), list):
            print('\n### Convert exclusions ###\n')
            print('%s (%d)\n' % (self._config['exclusions'], len(self._config['exclusions'])))
            
            _exclusions = []
            for exclusion in self._config['exclusions']:
                _exclusion = dict()
                for (name, value) in exclusion.items():
                    group = None
                    for psd in self._psds:
                        for layer in psd:
                            if layer.is_visible() and layer.is_group() and self._not_gif_layer(layer) and len(layer) > 0 and layer.name == name:
                                group = layer
                    if group is None:
                        print('Exclusion', exclusion, 'bad name:', name)
                        _exclusion = dict()
                        break

                    index = -1
                    for child in group:
                        index = index + 1
                        if child.name == value:
                            _exclusion[name] = index
                            break
                    
                    if _exclusion.get(name) is None:
                        print('Exclusion', exclusion, 'bad value:', value)
                
                if len(_exclusion) > 1:
                    _exclusions.append(_exclusion)
            
            self._config['exclusions'] = _exclusions
            
            print('\n%s (%d)' % (self._config['exclusions'], len(self._config['exclusions'])))
            print('\n### Convert exclusions ###\n')
    
    @classmethod
    def load(cls, names, config=None):
        if isinstance(config, dict):
            _config = config
        elif isinstance(config, str):
            with open(os.path.join(settings['psd_root'], config), 'r') as fo:
                _config = json.loads(fo.read())
        else:
            _config = None
        return cls(names[0], list(map(lambda name: PSDImage.open(os.path.join(settings['psd_root'], name + '.psd')), names)), config=_config)
    
    @property
    def max_length(self):
        length = 0
        for (_, _length) in reduce(lambda target1, psd: reduce(lambda target, layer: dict(target, **{layer.name: len(layer)}) if layer.is_visible() and layer.is_group() and self._not_gif_layer(layer) and len(layer) > 0 else target, psd, target1), self._psds, dict()).items():
            length = max(length, 1) * _length
        return length
    
    def execute(self, size=None, length=None, preview_config=None, inputs_dir=None, use_jpg=False):
        path = os.path.join(settings['psd_root'], self._name) if inputs_dir is None else os.path.join(settings['psd_root'], ('%s_full' % inputs_dir))
        ensure_dir_exists(path)

        if preview_config is None:
            _preview_config = None
        else:
            (width, height) = self._psds[0].size
            (w, h) = preview_config['thumb_size']
            scale = min(w / width, h / height)
            _preview_config = dict(
                column=preview_config['column'], 
                thumb_size=(int(width * scale), int(height * scale)), 
                dir=datetime.now().strftime('%Y%m%d%H%M%S')
            )
        
        def _new(target, gif_layer=None):
            im = Image.new('RGBA', self._psds[0].size, (255, 255, 255, 0))
            for layer in self._psds[0]:
                if layer.is_visible() is False:
                    continue
                
                _layer = None
                # if layer.is_group():
                #     if not len(layer) > 0:
                #         continue
                #     _layer = layer[target[layer.name]]
                # else:
                #     if target.get(layer.name) is None:
                #         _layer = layer
                #     else:
                #         for child in reduce(lambda children, psd: reduce(lambda layers, l: layers + [l] if l.is_visible() and l.is_group() and len(l) > 0 else layers, psd, children), self._psds[1:], []):
                #             if child.name == layer.name:
                #                 _layer = child[target[layer.name]]
                #                 break
                if not gif_layer is None and layer.name == gif_layer['name']:
                    _layer = gif_layer['layer']
                else:
                    if not layer.is_group() and target.get(layer.name) is None:
                        _layer = layer
                    else:
                        for child in reduce(lambda children, psd: reduce(lambda layers, l: layers + [l] if l.is_visible() and l.is_group() and self._not_gif_layer(l) and len(l) > 0 else layers, psd, children), self._psds, []):
                            if child.name == layer.name:
                                _layer = child[target[layer.name]]
                                break
                
                if _layer is None:
                    continue

                _layer.visible = True
                layer_image = _layer.composite()
                
                _, _, _, mask = layer_image.convert('RGBA').split()
                im.paste(layer_image, _layer.offset, mask=mask)
            
            if not has_transparency(self._psds[0]):
                im = im.convert('RGB')
                
                if Resource.ICC_PROFILE in self._psds[0].image_resources:
                    im = _apply_icc(im, self._psds[0].image_resources.get_data(Resource.ICC_PROFILE))
            
            if not size is None:
                (width, height) = im.size
                (w, h) = size
                scale = min(w / width, h / height)
                im = im.resize((int(width * scale), int(height * scale)))
            
            if use_jpg and not im.mode == 'RGB':
                im = im.convert('RGB')
            
            return im
        
        gif_layers = self._gif_layers()

        if not inputs_dir is None:
            def _(inputs, name):
                if name.startswith('.'):
                    return inputs
                
                if os.path.isdir(os.path.join(settings['psd_root'], inputs_dir, name)):
                    return inputs
                
                return inputs + [ list(map(int, os.path.splitext(name)[0].split('_'))) ]
            
            generator = self._generator_reverse(
                reduce(_, os.listdir(os.path.join(settings['psd_root'], inputs_dir)), []), 
                preview_config=_preview_config
            )
        elif not length is None:
            generator = self._generator_random(length, preview_config=_preview_config)
        else:
            generator = self._generator()
        
        for target in generator:
            if len(gif_layers) > 0:
                imgs = list(map(lambda gif_layer: _new(target, gif_layer=gif_layer), gif_layers))
                imgs[0].save(os.path.join(path, '_'.join(list(map(str, target.values()))) + '.gif'), save_all=True, append_images=imgs[1:], loop=self._config['gif'].get('loop', 0), duration=self._config['gif'].get('duration', 0))
            else:
                _new(target).save(os.path.join(path, '_'.join(list(map(str, target.values()))) + ('.jpg' if use_jpg else '.png')))
    
    def _gif_layers(self):
        try:
            for layer in reduce(lambda children, psd: reduce(lambda layers, layer: layers + [layer] if layer.is_visible() and layer.is_group() and layer.name in self._config['gif']['layers'] and len(layer) > 0 else layers, psd, children), self._psds, []):
                if layer.name == self._config['gif']['layers'][0]:
                    return list(map(lambda child: dict(name=self._config['gif']['layers'][0], layer=child), layer))
            return []
        except:
            return []
    
    def _not_gif_layer(self, layer):
        try:
            return not layer.name in self._config['gif']['layers']
        except:
            return True

    def _generator(self):
        layers = reduce(lambda layers1, psd: reduce(lambda layers, layer: dict(layers, **{layer.name: reduce(lambda indexes, _: indexes + [ len(indexes) ], layer, [])}) if layer.is_visible() and layer.is_group() and self._not_gif_layer(layer) and len(layer) > 0 else layers, psd, layers1), self._psds, dict())
        # layers = dict(list(map(lambda layer: (layer[0], layer[1][:2]), layers.items())))
        print(layers)
        print(reduce(lambda count, layer: count * len(layer[1]), layers.items(), 1))
        for t in reduce(lambda ts1, layer: reduce(lambda ts2, _: ts2 + ([ {layer[0]: len(ts2)} ] if len(ts1) == 0 else list(map(lambda target: dict(target, **{layer[0]: int(len(ts2) / len(ts1))}), ts1))), layer[1], []), layers.items(), []):
            if self._exclude(t):
                continue
            print(t)
            yield t
    
    def _generator_random(self, length, preview_config=None):
        targets = []
        while True:
            target = reduce(lambda target1, psd: reduce(lambda target, layer: dict(target, **{layer.name: random.randint(0, (len(layer) - 1))}) if layer.is_visible() and layer.is_group() and self._not_gif_layer(layer) and len(layer) > 0 else target, psd, target1), self._psds, dict())
            if target in targets:
                continue
            if self._exclude(target):
                continue
            print(target, '%d/%d' % (len(targets) + 1, length))
            yield target
            targets.append(target)

            if len(targets) == length:
                break

            if not preview_config is None and len(targets) % (preview_config['column'] * preview_config['column']) == 0:
                self._preview(targets, preview_config)
        
        if not preview_config is None:
            self._preview(targets, preview_config)
    
    def _generator_reverse(self, inputs, preview_config=None):
        els = reduce(lambda target1, psd: reduce(lambda target, layer: dict(target, **{layer.name: len(layer)}) if layer.is_visible() and layer.is_group() and self._not_gif_layer(layer) and len(layer) > 0 else target, psd, target1), self._psds, dict()).items()
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
            if self._exclude(target):
                continue
            print(target, '%d/%d' % (inputs.index(input) + 1, len(inputs)))
            yield target
            targets.append(target)

            if not preview_config is None and len(targets) % (preview_config['column'] * preview_config['column']) == 0:
                self._preview(targets, preview_config)
        
        if not preview_config is None:
            self._preview(targets, preview_config)
    
    def _exclude(self, target):
        try:
            for exclusion in self._config['exclusions']:
                exclude = True
                for (name, index) in exclusion.items():
                    if target[name] != index:
                        exclude = False
                        break
                if exclude:
                    return True
            return False
        except:
            return False
    
    def _preview(self, targets, config):
        try:
            path = os.path.join(settings['psd_root'], self._name, 'preview', config['dir'])
            ensure_dir_exists(path)

            print('\nPreviewing, save in', path)

            (width, height) = config['thumb_size']
            max_column = config['column']
            length = max_column * max_column
            index = -1
            for rg in ([targets[i:i+length] for i in range(0, len(targets), length)]):
                index = index + 1
                name = '%d-%d' % (index * length + 1, index * length + len(rg))
                
                if os.path.exists(os.path.join(path, name + '.png')):
                    continue
                
                print('Handling', name)

                with open(os.path.join(path, name + '.json'), 'wb') as fo:
                    fo.write(json.dumps(rg).encode())
                print(name + '.json', 'Success.')
                
                row = math.ceil(len(rg) / max_column)
                column = max_column if row > 1 else len(rg)
                (margin_x, margin_y) = (15, 15)
                
                img = Image.new('RGBA', (column * width + (column + 1) * margin_x, row * height + (row + 1) * margin_y), (255, 255, 255, 255))
                draw = ImageDraw.Draw(img)
                draw.text((0, 0), '%s (%s)' % (config['dir'], name), fill='black')
                for target in rg:
                    y = margin_y + math.floor(rg.index(target) / max_column) * (height + margin_y)
                    x = margin_x + rg.index(target) % max_column * (width + margin_x)

                    target_image = Image.open(os.path.join(settings['psd_root'], self._name, '_'.join(list(map(str, target.values()))) + '.png')).resize(config['thumb_size'])
                    _, _, _, m = target_image.convert('RGBA').split()
                    img.paste(target_image, (x, y), mask=m)
                    draw.text((x, y + height), '%d:%s' % (index * length + rg.index(target) + 1, '_'.join(list(map(str, target.values())))), fill='black')

                img.save(os.path.join(path, name + '.png'))
                print(name + '.png', 'Success.')
            print('')
        except Exception as e:
            print('Preview Error', e)
    
    def sts_all(self):
        path = os.path.join(settings['psd_root'], self._name)
        if not (os.path.exists(path) and os.path.isdir(path)):
            return
        self.sts(reduce(lambda inputs, name: (inputs if name.startswith('.') or os.path.isdir(os.path.join(path, name)) else inputs + [ list(map(int, name.split('.')[0].split('_'))) ]), os.listdir(path), []))

    def sts(self, inputs):
        els = reduce(lambda target1, psd: reduce(lambda target, layer: dict(target, **{layer.name: dict(values=list(map(lambda child: dict(name=child.name, count=0), layer)), count=0)}) if layer.is_visible() and layer.is_group() and self._not_gif_layer(layer) and len(layer) > 0 else target, psd, target1), self._psds, dict())
        for target in self._generator_reverse(inputs):
            for (name, index) in target.items():
                els[name]['values'][index]['count'] = els[name]['values'][index]['count'] + 1
                els[name]['count'] = els[name]['count'] + 1
        print(els)
        
        img = Image.new('RGBA', (50 + 1000 + 1000 + 50, 50 * (len(els) + 1) + 50 * reduce(lambda count, el: count + len(el['values']), els.values(), 0)), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(font=os.path.join(font_root, 'msyh.ttf'), size=40)
        x = y = 50
        for (name, el) in els.items():
            draw.text((x, y + (len(el['values']) * 50 - 50) / 2), '%s (%d)' % (name, el['count']), fill='black', font=font)
            x = x + 1000
            for value in el['values']:
                draw.text((x, y), '%s (%d, %.2f%%)' % (value['name'], value['count'], round(value['count'] / el['count'] * 100, 2) if el['count'] > 0 else 0), fill='black', font=font)
                y = y + 50
            x = 50
            y = y + 50
        path = os.path.join(settings['psd_root'], self._name + '_sts_%s.png' % datetime.now().strftime('%Y%m%d%H%M%S'))
        print('\nSaving in', path)
        img.save(path)
    
    def sts_dir(self, dir):
        def _(inputs, name):
            if name.startswith('.'):
                return inputs
            
            if os.path.isdir(os.path.join(settings['psd_root'], dir, name)):
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
            
            return dict(inputs, **{_origin_name: dict(origin_name=(_origin_name + ext), id=id, name=('' if _name is None else (_name + ext)))})
        
        inputs = reduce(_, sorted(os.listdir(os.path.join(settings['psd_root'], dir))), dict())
        els, targets = self.sts1(inputs)

        # with open(os.path.join(settings['psd_root'], dir + '_sts_els.json'), 'wb') as fo:
        #     fo.write(json.dumps(els).encode())
        
        # with open(os.path.join(settings['psd_root'], dir + '_sts_targets.json'), 'wb') as fo:
        #     fo.write(json.dumps(targets).encode())
        
        workbook = xlwt.Workbook()

        # write targets
        targets_sheet = workbook.add_sheet('Targets')
        general_names = ['origin_name', 'id', 'name']
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
            targets_sheet.col(col).width = 8000 if col == 0 else 3000
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
            sheet.col(0).width = 5000
            sheet.col(1).width = 5000
            sheet.col(2).width = 5000
        # write els
        
        workbook.save(os.path.join(settings['psd_root'], dir + '_sts.xlsx'))
    
    def sts1(self, inputs):
        els = reduce(lambda target1, psd: reduce(lambda target, layer: dict(target, **{layer.name: dict(values=list(map(lambda child: dict(name=child.name, count=0), layer)), count=0)}) if layer.is_visible() and layer.is_group() and self._not_gif_layer(layer) and len(layer) > 0 else target, psd, target1), self._psds, dict())
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
