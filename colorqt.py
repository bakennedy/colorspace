#!/usr/bin/env python
'''
Created on Apr 11, 2011

@author: brian
'''

import sys
import simplejson as json
from colormath.color_objects import RGBColor
from PIL import Image
import progress
from collections import defaultdict


def color_from_hex(hexe):
    a = RGBColor()
    a.set_from_rgb_hex(hexe)
    return a.convert_to("lab")


data = json.load(open("colors.json"))
color_names = [(color_from_hex(v), k) for k, v in data.items()]


def get_image_colors(filename):
    im = Image.open(filename)
    width, height = im.size
    if height > 600 or width > 600:
        if height > width:
            nw = int(round((600.0 * width) / height))
            nh = 600
        else:
            nh = int(round((600.0 * height) / width))
            nw = 600
        print("Shrinking %d x %d to %d x %d" % (width, height, nw, nh))
        im = im.resize((nw, nh), Image.ANTIALIAS)
        print("Shrunk")
    return list(im.getdata())


def qt_cluster(pixels, unused_colors, count=10, threshold=2.45):
    top_colors = []
    while len(pixels) > 0 and len(top_colors) < count:
        max_color = None
        max_neighbors = []
        max_quantity = 0
        max_distortion = 0
        max_index = None
        prog = progress.ProgressMeter(total=len(unused_colors))
        for i in xrange(len(unused_colors)):
            last_count, color = unused_colors[i]
            if last_count is not None and last_count < max_quantity:
                break
            neighbors = []
            quantity = 0
            distortion = 0
            o = len(pixels) - 1
            while o >= 0:
                pixel, qty = pixels[o]
                dist = color[0].delta_e(pixel, mode='cie2000')
                if dist < threshold:
                    neighbors.append(o)
                    quantity += qty
                    distortion += dist
                unused_colors[i][0] = quantity 
                o -= 1
            if quantity > max_quantity or (
               quantity == max_quantity and
               distortion < max_distortion):
                max_index = i
                max_color = color
                max_neighbors = neighbors
                max_distortion = distortion
                max_quantity = quantity
            prog.update(1)
        prog.set(100)
        if max_color is None:
            break
        print("%s\t%d of %d" % (max_color[1], max_quantity, len(pixels))) 
        top_colors.append((max_color[1], (max_color[0], max_color[0])))
        del unused_colors[max_index]
        unused_colors.sort()
        unused_colors.reverse()
        for pixel in max_neighbors:
            del pixels[pixel]
    return top_colors


if __name__ == "__main__":
    for filename in sys.argv[1:]:
        pixels = defaultdict(int)
        for p in get_image_colors(filename):
            pixels[p] += 1
        pixels = [(RGBColor(*p).convert_to("lab"), c) for p, c in pixels.items()]
        pixels.sort()
        pixels.reverse()
        top_colors = qt_cluster(pixels, [[None, c] for c in color_names], threshold=10.0)
