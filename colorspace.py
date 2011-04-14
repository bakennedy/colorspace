#!/usr/bin/env python
'''
Created on Apr 11, 2011

@author: brian
'''

import sys
import simplejson as json
import pygtk
pygtk.require('2.0')
import gtk, gobject, cairo
from PIL import Image
from scipy.stats import gmean
from scipy import sqrt
from scipy.cluster import vq
import numpy
from colormath.color_objects import RGBColor
import progress


def color_from_hex(hexe):
    a = RGBColor()
    a.set_from_rgb_hex(hexe)
    return a


data = json.load(open("colors.json"))
color_names = [(color_from_hex(v), k) for k, v in data.items()]


def name_color(unnamed):
    def comparator(x):
        return x[0].delta_e(unnamed, mode='cmc', pl=1, pc=1)
    color, name = min(color_names, key=comparator)
    return name, color


# Create a GTK+ widget on which we will draw using Cairo
class ColorComparison(gtk.DrawingArea):
    
    # Draw in response to an expose-event
    __gsignals__ = { "expose-event": "override" }


    # Handle the expose-event by drawing
    def do_expose_event(self, event):

        # Create the cairo context
        cr = self.window.cairo_create()

        # Restrict Cairo to the exposed area; avoid extra work
        cr.rectangle(0, 0, *self.window.get_size())
        cr.clip()
        self.draw(cr, *self.window.get_size())

    def draw(self, cr, width, height):
        # Fill the background with gray
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.rectangle(0, 0, width, height)
        cr.fill()
        for n, (actual, choice) in enumerate(self.color_pairs):
            cr.set_source_rgb(*actual)
            cr.rectangle(20, 20+n*80, 200, 60)
            cr.fill()
            cr.set_source_rgb(*choice)
            cr.rectangle(220, 20+n*80, 200, 60)
            cr.fill()
    
    def set_colors(self, color_pairs):
        def n(c):
            return (c.rgb_r / 255.0, c.rgb_g / 255.0, c.rgb_b / 255.0)
        self.color_pairs = [map(n, p) for p in color_pairs]

# GTK mumbo-jumbo to show the widget in a window and quit when it's closed
def run(Widget, colors):
    window = gtk.Window()
    window.set_size_request(440, 840)
    window.connect("delete-event", gtk.main_quit)
    widget = Widget()
    widget.set_colors(colors)
    window.add(widget)
    widget.show()
    window.present()
    gtk.main()

def get_image_center(filename, radius=1):
    im = Image.open(filename)
    pixels = im.load() # this is not a list
    width, height = im.size
    cx, cy = width / 2.0, height / 2.0
    samples = []
    limit = radius**2
    for y in xrange(int(cy - radius), int(cy + radius + 1)):
        dist = sqrt(limit - (y - cy)**2)
        for x in xrange(int(cx - dist), int(cx + dist + 1)):
            samples.append(pixels[x, y])
    return RGBColor(*gmean(samples, axis=0))

def qt_cluster(pixels, unused_colors, count=10, threshold=2.45):
    top_colors = []
    print("Top %d color:" % (len(top_colors)+1))
    while len(pixels) > 0 and len(top_colors) < count:
        max_color = None
        max_neighbors = []
        max_distortion = 0
        max_index = None
        prog = progress.ProgressMeter(total=len(unused_colors))
        for i in xrange(len(unused_colors)):
            last_count, color = unused_colors[i]
            if last_count is not None and last_count < len(max_neighbors):
                break
            neighbors = []
            distortion = 0
            for pixel in pixels:
                dist = color[0].delta_e(pixel, mode='cie2000')
                if dist < threshold:
                    neighbors.append(pixel)
                    distortion += dist
            if last_count is None:
                unused_colors[i][0] = len(neighbors) 
            if len(neighbors) > len(max_neighbors) or (
               len(neighbors) == len(max_neighbors) and
               distortion < max_distortion):
                max_index = i
                max_color = color
                max_neighbors = neighbors
                max_distortion = distortion
            prog.update(1)
        if max_color is None:
            break
        print(max_color[1])
        top_colors.append((max_color[1], (max_color[0], max_color[0])))
        del unused_colors[max_index]
        unused_colors.sort()
        unused_colors.reverse()
        for pixel in max_neighbors:
            pixels.remove(pixel)
    return top_colors

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

def kmean_cluter(pixels, count=10):
    centroids, distortion = vq.kmeans(pixels, count, iter=10, thresh=0.0001)
    targets = [RGBColor(*c) for c in centroids]
    color_pairs = []
    for target in targets:
        name, color = name_color(target)
        color_pairs.append((name, (target, color)))
    color_pairs.sort()
    for name, foo in color_pairs:
        print(name)
    run(ColorComparison, zip(*color_pairs)[1])


if __name__ == "__main__":
    for filename in sys.argv[1:]:
        pixels = [RGBColor(*p) for p in get_image_colors(filename)]
        top_colors = qt_cluster(pixels, [[None, c] for c in color_names])
    run(ColorComparison, zip(*top_colors)[1])
    #pass