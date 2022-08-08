# -*- encoding: utf-8 -*-

from functools import reduce
import math
from PIL import Image, ImageDraw, ImageFont
from settings import image_root, font_root
import os
import os.path
from util.dir import ensure_dir_exists
import random
import shutil
import cv2
from skimage.measure import regionprops

class ImageAid:
    def tint(self, dir, name, config, save_main=False, reset=False):
        print('\nexecuting', name)

        path = os.path.join(image_root, dir, name.split('.')[0])

        if reset and os.path.exists(path):
            shutil.rmtree(path)
        
        ensure_dir_exists(path)

        source_img = Image.open(os.path.join(image_root, dir, name)).convert('RGBA')

        try:
            img = Image.open(os.path.join(path, 'b_' + '_'.join(list(map(str, config['background']['t']))) + '.png'))
        except:
            img = source_img.copy()
            width, height = img.size
            print('clearing...')
            # min_x = width
            # max_x = 0
            # min_y = height
            # max_y = 0
            fr, fg, fb = config['background']['f']
            for i in range(0, width):
                for j in range(0, height):
                    r, g, b, a = img.getpixel((i, j))
                    if r > fr and g > fg and b > fb or a < 255:
                        img.putpixel((i, j), config['background']['t'])
                    # else:
                    #     min_x = min(min_x, i)
                    #     max_x = max(max_x, i)
                    #     min_y = min(min_y, j)
                    #     max_y = max(max_y, j)
            # img = img.crop((max(min_x - 10, 0), max(min_y - 10, 0), min(max_x + 10, width), min(max_y + 10, height)))
            if save_main:
                img.save(os.path.join(path, 'b_' + '_'.join(list(map(str, config['background']['t']))) + '.png'))

        random_count = reduce(lambda count, target: count + (0 if target.get('random') is None else (len(target['random'].get('backgrounds', [])) + len(target['random'].get('images', [])))), config['targets'], 0)
        random_index = None if random_count == 0 else random.randint(0, random_count - 1)
        random_count = 0

        tr, tg, tb, ta = config['background']['t']
        for target in config['targets']:
            print('generating', target)
            try:
                main_img = Image.open(os.path.join(path, 'f_' + '_'.join(list(map(str, target['foreground']))) + '.png'))
            except:
                main_img = img.copy()

                if not target.get('foreground') is None:
                    w, h = main_img.size
                    for i in range(0, w):
                        for j in range(0, h):
                            r, g, b, a = main_img.getpixel((i, j))
                            if r == tr and g == tg and b == tb and a == ta:
                                continue
                            else:
                                main_img.putpixel((i, j), target['foreground'])
                    if save_main:
                        main_img.save(os.path.join(path, 'f_' + '_'.join(list(map(str, target['foreground']))) + '.png'))
            
            w, h = main_img.size
            _, _, _, mask = main_img.split()

            random_backgrounds = []
            random_images = []
            if not (random_index is None or target.get('random') is None):
                index = random_index - random_count
                count = len(target['random'].get('backgrounds', []))
                if index >= 0 and index < count:
                    random_backgrounds.append(target['random']['backgrounds'][index])
                random_count = random_count + count

                index = random_index - random_count
                count = len(target['random'].get('images', []))
                if index >= 0 and index < count:
                    random_images.append(target['random']['images'][index])
                random_count = random_count + count

            for background in target.get('backgrounds', []) + random_backgrounds:
                print('background =', background)
                width, height = source_img.size
                new_image = Image.new('RGBA', (width, height), background)
                new_image.paste(main_img, (max(0, int((width - w) / 2)), max(0, int((height - h) / 2))), mask=mask)
                new_image.save(os.path.join(path, ('' if target.get('foreground') is None else '_'.join(list(map(str, target['foreground'])))) + '_' + '_'.join(list(map(str, background))) + '.png'))
            
            for image in target.get('images', []) + random_images:
                print('image =', image)
                try:
                    bg_image = Image.open(os.path.join(image_root, image)).convert('RGBA')
                    width, height = bg_image.size
                    new_image = Image.new('RGBA', (width, height), (255, 255, 255, 0))
                    _, _, _, m = bg_image.split()
                    new_image.paste(bg_image, (0, 0), mask=m)

                    scale = min(width / w, height / h)
                    if scale < 1:
                        (w1, h1) = (int(w * scale), int(h * scale))
                        resized_main_img = main_img.resize((w1, h1))
                        _, _, _, m = resized_main_img.split()
                        new_image.paste(resized_main_img, (max(0, int((width - w1) / 2)), max(0, int((height - h1) / 2))), mask=m)
                    else:
                        new_image.paste(main_img, (max(0, int((width - w) / 2)), max(0, int((height - h) / 2))), mask=mask)

                    new_image.save(os.path.join(path, ('' if target.get('foreground') is None else '_'.join(list(map(str, target['foreground'])))) + '_' + image.split('.')[0] + '.png'))
                except Exception as e:
                    print(e)
    
    def color(self, dir, name, tint_config, config, prefix, min_area, max_colors=None):
        self.tint(
            dir, 
            name, 
            dict(
                background=tint_config['background'], 
                targets=list(map(lambda target: dict(foreground=target['foreground'], backgrounds=[target['background']]), config['targets'].values()))
            )
        )

        path = os.path.join(image_root, dir, name.split('.')[0])

        for (target_key, target) in config['targets'].items():
            print('\ntarget = %s: %s' % (target_key, target))

            _, labels = cv2.connectedComponents(
                cv2.imread(os.path.join(path, '_'.join(list(map(str, target['foreground']))) + '_' + '_'.join(list(map(str, target['background']))) + '.png'), cv2.IMREAD_GRAYSCALE),
                connectivity=8
            )
            props = regionprops(labels)

            for (colors_key, (colors, _targets)) in config['colors'].items():
                if not target_key in _targets:
                    continue
                
                print('colors = %s: %s' % (colors_key, colors))
                cs = colors if max_colors is None or max_colors > len(colors) else random.sample(colors, max_colors)

                if target.get('reverse') is True:
                    try:
                        img = Image.open(os.path.join(path, '_'.join(list(map(str, target['background']))) + '_' + '_'.join(list(map(str, target['foreground']))) + '.png'))
                    except:
                        self.tint(
                            dir, 
                            name, 
                            dict(
                                background=tint_config['background'], 
                                targets=[dict(foreground=target['background'], backgrounds=[target['foreground']])]
                            )
                        )
                        img = Image.open(os.path.join(path, '_'.join(list(map(str, target['background']))) + '_' + '_'.join(list(map(str, target['foreground']))) + '.png'))
                else:
                    img = Image.open(os.path.join(path, '_'.join(list(map(str, target['foreground']))) + '_' + '_'.join(list(map(str, target['background']))) + '.png'))
                
                for prop in props:
                    if prop.area < min_area:
                        continue
                    
                    bbox = self._convert_bbox(prop.bbox)
                    if bbox == img.getbbox():
                        color = (lambda bcs: None if len(bcs) == 0 else bcs[random.randint(0, (len(bcs) - 1))])((lambda bcs: bcs if max_colors is None or max_colors > len(bcs) else random.sample(bcs, max_colors))(config.get('background_colors', [])))
                        if color is None:
                            continue
                    else:
                        color = cs[random.randint(0, (len(cs) - 1))]# cs[props.index(prop) % len(cs)]
                    print('Color %s to %s (%d coords). [%d/%d]' % (color, bbox, prop.area, props.index(prop) + 1, len(props)))
                    for (y, x) in prop.coords:
                        img.putpixel((x, y), color)
                img.save(os.path.join(path, 'color_%s_%s_%s.png' % (prefix, target_key, colors_key)))

                # if target.get('reverse') is True:
                #     w, h = img.size
                #     for i in range(0, w):
                #         for j in range(0, h):
                #             c = img.getpixel((i, j))
                #             if c == target['foreground']:
                #                 img.putpixel((i, j), target['background'])
                #             elif c == target['background']:
                #                 img.putpixel((i, j), target['foreground'])
                #             else:
                #                 continue
                #     img.save(os.path.join(path, 'color_%s_%s_%s_reverse.png' % (prefix, target_key, colors_key)))
                print('')
        
        if 'combines' in config and len(config['combines']) > 0:
            target_keys = ['area', 'line']

            if reduce(lambda ret, key: (ret and key in config['targets']), target_keys, True):
                def _props(target):
                    _, labels = cv2.connectedComponents(
                        cv2.imread(os.path.join(path, '_'.join(list(map(str, target['foreground']))) + '_' + '_'.join(list(map(str, target['background']))) + '.png'), cv2.IMREAD_GRAYSCALE),
                        connectivity=8
                    )
                    return regionprops(labels)
                
                props_dict = reduce(lambda props, key: dict(props, **{key: _props(config['targets'][key])}), target_keys, dict())

                for combine in config['combines']:
                    colors_dict = reduce(lambda colors, key: dict(colors, **{key: config['colors'][combine[key]][0]}), target_keys, dict())                    
                    print('[COMBINE]\n%s\n[COMBINE]' % '\n'.join(list(map(lambda c: '%s_colors = %s' % (c[0], c[1]), colors_dict.items()))))
                    colors_dict = reduce(lambda colors, c: dict(colors, **{c[0]: (c[1] if max_colors is None or max_colors > len(c[1]) else random.sample(c[1], max_colors))}), colors_dict.items(), dict())
                    
                    target_key = target_keys[1] if combine.get('reverse') is True else target_keys[0]
                    img = Image.open(os.path.join(path, '_'.join(list(map(str, config['targets'][target_key]['foreground']))) + '_' + '_'.join(list(map(str, config['targets'][target_key]['background']))) + '.png'))
                    
                    for key in target_keys:
                        for prop in props_dict[key]:
                            if prop.area < min_area:
                                continue

                            bbox = self._convert_bbox(prop.bbox)
                            if bbox == img.getbbox():
                                color = (lambda bcs: None if len(bcs) == 0 else bcs[random.randint(0, (len(bcs) - 1))])((lambda bcs: bcs if max_colors is None or max_colors > len(bcs) else random.sample(bcs, max_colors))(config.get('background_colors', [])))
                                if color is None:
                                    continue
                            else:
                                color = colors_dict[key][random.randint(0, (len(colors_dict[key]) - 1))]
                            print('[%s] Color %s to %s (%d coords). [%d/%d]' % (key.upper(), color, bbox, prop.area, props_dict[key].index(prop) + 1, len(props_dict[key])))
                            for (y, x) in prop.coords:
                                img.putpixel((x, y), color)
                    
                    img.save(os.path.join(path, 'color_%s_combine_%s.png' % (prefix, '_'.join(list(map(lambda key: combine[key], target_keys))))))
                    print('')
    
    def _convert_bbox(self, bbox):
        (min_row, min_col, max_row, max_col) = bbox
        return (min_col, min_row, max_col, max_row)
    
    def seal(self, input, output, signet, cbox=None):
        im = Image.open(input)
        w, h = im.size

        if cbox is None or cbox.get('margin') is None:
            x, y = (0, 0)
        else:
            x, y = cbox['margin']
        
        if cbox is None or cbox.get('size') is None:
            s = signet
        else:
            s = signet.resize(cbox['size'])
        w1, h1 = s.size
        
        if cbox is None or cbox['corner'] in ['TR', 'BR']:
            x = w - w1 - x
        
        if cbox is None or cbox['corner'] in ['BL', 'BR']:
            y = h - h1 - y
        
        _, _, _, mask = s.convert('RGBA').split()
        im.paste(s, (x, y), mask=mask)
        im.save(output)
    
    def gif(self, dir, name, size=None, loop=0, duration=0):
        path = os.path.join(image_root, dir, name)
        
        def _check(n):
            if n.startswith('.'):
                return []

            if os.path.isdir(os.path.join(path, n)):
                return []
            
            return [n]
        
        ns = reduce(lambda ns, n: ns + _check(n), os.listdir(path), [])
        ns.sort()
        ims = list(map(lambda n: Image.open(os.path.join(path, n)), ns))

        def _resize(im, size):
            w, h = im.size
            nw, nh = size
            if w == nw and h == nh:
                return im
            scale = max(nw / w, nh / h)
            new_im = im.resize((int(w * scale), int(h * scale)))
            w, h = new_im.size
            return new_im.crop((int((w - nw) / 2), int((h - nh) / 2), nw, nh)).resize(size)
        
        fit_size = (min(list(map(lambda im: im.size[0], ims))), min(list(map(lambda im: im.size[1], ims))))
        if not size is None:
            (width, height) = fit_size
            (w, h) = size
            scale = min(w / width, h / height)
            fit_size = (int(width * scale), int(height * scale))
        
        ims = list(map(lambda im: _resize(im, fit_size), ims))
        ims[0].save(os.path.join(image_root, dir, name + ('' if size is None else '_' + '_'.join(list(map(str, size)))) + '.gif'), save_all=True, append_images=ims[1:], loop=loop, duration=duration)
    
    def block_info(self, input, output, logo, label, force_break=False, background=False):
        margin_x, margin_y = (5, 0)
        sep = 5

        _logo = logo.resize((15, 15)).convert('RGBA')
        logo_w, logo_h = _logo.size

        im = Image.open(input)
        w, h = im.size

        font = ImageFont.truetype(font=os.path.join(font_root, 'msyh.ttf'), size=10)
        draw = ImageDraw.Draw(im)
        
        def calculate():
            max_w = w - margin_x - logo_w - sep - margin_x
            labels = list(map(lambda l: [l], label)) if force_break else [label]
            while True:
                l = '\n'.join(list(map(lambda ls: ' '.join(ls), labels)))
                lw, lh = draw.textsize(l, font=font)
                if lw > max_w and len(labels) < len(label):
                    labels = reduce(lambda lss, ls: lss + list(filter(lambda nls: len(nls) > 0, [ls[:max(1, math.floor(len(ls) / 2))], ls[max(1, math.floor(len(ls) / 2)):]])), labels, [])
                    continue
                return l, min(lw, max_w), lh
        
        _label, label_w, label_h = calculate()

        hh = margin_y + max(logo_h, label_h) + margin_y

        _, _, _, mask = _logo.split()
        im.paste(_logo, (margin_x, h - hh + int((hh - logo_h) / 2)), mask=mask)

        def cv(v):
            if v < 55 or v > 200:
                return 255 - v
            elif v > 100:
                return 0
            else:
                return 255

        if background:
            # draw.bitmap((margin_x + logo_w + sep, h - hh + int((hh - label_h) / 2)), Image.new('RGBA', (label_w, label_h), (0, 0, 0, 75)), fill=(0, 0, 0, 75))
            draw.bitmap((0, h - hh + margin_y), Image.new('RGBA', (margin_x + logo_w + sep + label_w + margin_x, hh - margin_y - margin_y), (0, 0, 0, 75)), fill=(0, 0, 0, 75))
        
        draw.text(
            (margin_x + logo_w + sep, h - hh + int((hh - label_h) / 2)), 
            _label, 
            fill=(255, 255, 255) if background else tuple(map(cv, im.convert('RGB').getpixel((margin_x + logo_w + sep, h - int(hh / 2))))), 
            font=font
        )

        im.save(output)