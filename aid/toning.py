# -*- encoding: utf-8 -*-

from functools import reduce
from PIL import Image
from psd_tools import PSDImage
from settings import toning as settings
import os
import os.path
import json
from error import BaseError
from util.dir import ensure_dir_exists

class ModelError(BaseError): pass

KIND = ['eq', 'lte', 'gte', 'range']

class ToningAid:
    @staticmethod
    def valid(model):
        if not isinstance(model, dict):
            raise ModelError('model')
        
        if not isinstance(model['name'], str):
            raise ModelError('name')
        
        path = os.path.join(settings['psd_root'], model['psd'])

        if not os.path.exists(path):
            raise ModelError('psd')
        
        if not isinstance(model['layers'], dict):
            raise ModelError('layers')
        
        psd = PSDImage.open(path)
        
        for (name, config) in model['layers'].items():
            if reduce(lambda result, layer: (layer if layer.is_group() is False and layer.name == name else None) if result is None else result, psd, None) is None:
                raise ModelError('layer name')
            
            if not (isinstance(config['from'], list) and isinstance(config['to'], list)):
                raise ModelError('layer from and/or to')
            
            for color in config['from']:
                if not (isinstance(color, list) and len(color) == 3):
                    raise ModelError('layer from color')
                
                for el in color:
                    if not isinstance(el, dict):
                        raise ModelError('layer from color el')
                    
                    if el['kind'] in list(set(KIND).difference(set(['range']))):
                        if not (isinstance(el['value'], int) and el['value'] >= 0 and el['value'] <= 255):
                            raise ModelError('layer from color el value')
                    elif el['kind'] == 'range':
                        if not (isinstance(el['value'], list) and len(el['value']) == 2):
                            raise ModelError('layer from color el value')
                        
                        (start, end) = el['value']
                        if not (isinstance(start, int) and start >= 0 and start <= 255 and isinstance(end, int) and end >= 0 and end <= 255 and start <= end):
                            raise ModelError('layer from color el value')
                    else:
                        raise ModelError('layer from color el kind')
            
            for colors in config['to']:
                if not (isinstance(colors, list) and len(config['from']) == len(colors)):
                    raise ModelError('layer to colors')
                
                for color in colors:
                    if not (isinstance(color, list) and len(color) == 3):
                        raise ModelError('layer to color')
                    
                    for el in color:
                        if not (isinstance(el, int) and el >= 0 and el <= 255):
                            raise ModelError('layer to color el')
        
        if not model.get('exclusions') is None:
            if not isinstance(model['exclusions'], list):
                raise ModelError('exclusions')
            
            for exclusion in model['exclusions']:
                if not isinstance(exclusion, dict):
                    raise ModelError('exclusion type')
                
                if not len(exclusion) > 1:
                    raise ModelError('exclusion len')
                
                for (name, index) in exclusion.items():
                    if model['layers'].get(name) is None:
                        raise ModelError('exclusion name')
                    
                    if index < 0 or index >= len(model['layers'][name]['to']):
                        raise ModelError('exclusion index')
    
    @staticmethod
    def compareColor(e, el):
        if el['kind'] == 'eq':
            return e == el['value']
        elif el['kind'] == 'lte':
            return e <= el['value']
        elif el['kind'] == 'gte':
            return e >= el['value']
        elif el['kind'] == 'range':
            (start, end) = el['value']
            return e >= start and e<= end
        else:
            return False

    def __init__(self, model):
        ToningAid.valid(model)
        self._model = model
    
    @classmethod
    def load(cls, name):
        path = os.path.join(settings['data_root'], name + settings['data_suffix'])
        with open(path, 'r') as fo:
            return cls(json.loads(fo.read()))
    
    def save(self):
        path = os.path.join(settings['data_root'], self._model['name'] + settings['data_suffix'])
        ensure_dir_exists(os.path.dirname(path))

        with open(path, 'wb') as fo:
            fo.write(json.dumps(self._model).encode())
    
    def execute(self):
        path = os.path.join(settings['psd_root'], self._model['name'])
        ensure_dir_exists(path)

        psd = PSDImage.open(os.path.join(settings['psd_root'], self._model['psd']))

        for target in self._generator():
            print(list(map(lambda t: (t[0], self._model['layers'][t[0]]['to'][t[1]]), target.items())))
            img = Image.new('RGBA', psd.size, (255, 255, 255, 0))
            for layer in psd:
                if layer.is_group():
                    continue
                layer_image = layer.composite()

                config = self._model['layers'].get(layer.name)

                if not config is None:
                    pair = list(zip(config['from'], config['to'][target[layer.name]]))
                    width, height = layer_image.size

                    for i in range(0, width):
                        for j in range(0, height):
                            r, g, b, a = layer_image.getpixel((i, j))
                            for ((fr, fg, fb), (tr, tg, tb)) in pair:
                                if ToningAid.compareColor(r, fr) and ToningAid.compareColor(g, fg) and ToningAid.compareColor(b, fb):
                                    layer_image.putpixel((i, j), (tr, tg, tb, a))
                
                _, _, _, mask = layer_image.convert('RGBA').split()
                img.paste(layer_image, layer.offset, mask=mask)
            img.save(os.path.join(path, ''.join(list(map(str, target.values()))) + '.png'))
    
    def _exclude(self, target):
        if self._model.get('exclusions') is None:
            return False
        
        for exclusion in self._model['exclusions']:
            exclude = True
            for (name, index) in exclusion.items():
                if target[name] != index:
                    exclude = False
                    break
            if exclude:
                return True
        
        return False

    def _generator(self):
        for t in reduce(lambda ts1, layer: reduce(lambda ts2, _: ts2 + ([ {layer[0]: len(ts2)} ] if len(ts1) == 0 else list(map(lambda target: dict(target, **{layer[0]: int(len(ts2) / len(ts1))}), ts1))), layer[1]['to'], []), self._model['layers'].items(), []):
            if self._exclude(t):
                continue
            yield t