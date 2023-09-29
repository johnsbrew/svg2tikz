#!/usr/bin/env python3

import math
import pprint
import xml.etree.ElementTree as xml
import argparse

from lib import config,svgparser,colors,emitter
from lib.defs import *
from lib.mxparser import MxGraph

from lib.common import *

# from csv2svg
class Polygon(object):
  def __init__(self, points = [], SCALE =1):
    self.points = points
    self.scale = SCALE
    pass

  def push(self,point):
    self.points.append(point)

  def getSurface(self):
    pts = self.points + [self.points[0]]
    pts = list(map(lambda x: (x[0]*self.scale, x[1]*self.scale), pts))
    surface = 0
    prev = pts[0]
    for pt in pts[1:]:
      surface += prev[0] * pt[1] - prev[1] * pt[0]
      prev = pt
    surface = abs(surface / 2)
    return surface

  def getTikz(self, color = "red"):
    elements = []
    elements.append("({},-{})".format(f(self.points[0][0]), f(self.points[0][1])))
    for pt in self.points[1:]:
      elements.append(" -- ({},-{})".format(f(pt[0]), f(pt[1])))
    elements.append(" -- cycle")
    
    tikz = {
      'draw': True,
      'cmd': 'fill',
      'opts': {'color': color, 'fill opacity': '0.2'},
      'path': ''.join(elements)
    }

    return tikz
  
  def getPos(self, a, b):
    x = (a[0]+b[0])/2 + 20 #0.2 * abs(b[1]-a[1])
    y = (a[1]+b[1])/2 + 20 #0.2 * abs(b[0]-a[0])
    return (x,y)

  def getLength(self, a, b):
    x = math.pow(a[0]-b[0], 2)
    y = math.pow(a[1]-b[1], 2)
    return math.sqrt(x+y)

  def getAngle(self, a, b, length):
    # goal = finding angle between an horizontal axis from right to left with origin A and B
    angle = math.acos((b[0]-a[0])/length)/math.pi*180
    # we operate in reverse order (geographic angles) & we need to translate the 180° onto 360°
    angle = angle + 180 if b[1] > a[1] else angle
    # must correct the translation in some cases
    angle = 180 - angle if b[1] < a[1] and b[0] < a[0] else angle 
    return angle

  def printIterativeDirections(self):
    points = self.points if self.points[0] == self.points[-1] else self.points + [self.points[0]]
    pts = list(map(lambda x: (x[0]*self.scale, x[1]*self.scale), points))
    nodes = []
    for i in range(0, len(pts)-1):
      length = self.getLength(pts[i], pts[i+1])
      angle = self.getAngle(pts[i], pts[i+1], length)
      # str.replace to match french number format in excel ...s
      # print('{}->{}'.format(points[i], points[i+1]))
      print("{} {}".format(f(length*100).replace('.',','), f(angle).replace('.',',')))

  def getLengths(self, color="black"):
    points = self.points if self.points[0] == self.points[-1] else self.points + [self.points[0]]
    pts = list(map(lambda x: (x[0]*self.scale, x[1]*self.scale), points))
    nodes = []
    for i in range(0, len(pts)-1):
      length = self.getLength(pts[i], pts[i+1])
      pos = self.getPos(points[i], points[i+1])

      tikz = {
        'draw': True, # False to preserve empty containers in the IR
        'cmd': 'node', 
        'opts': {'align': 'left', 'font': '\\huge', 'color': color},
        'path': "at ({},-{})".format(f(pos[0]), f(pos[1])),
        'content': {
          'value': f(length)
        }, 
        'extra': [],
        'transforms': {}
      }
      nodes.append({'tikz': tikz})

    return nodes

  def getCenter(self):
    minX = self.points[0][0]
    maxX = self.points[0][0]
    minY = self.points[0][1]
    maxY = self.points[0][1]

    for pt in self.points[1:]:
      if pt[0] < minX:
        minX = pt[0]
      elif pt[0] > maxX:
        maxX = pt[0]
      if pt[1] < minY:
        minY = pt[1]
      elif pt[1] > maxY:
        maxY = pt[1]

    return ((minX + maxX)/2, (minY + maxY)/2)

  def getBarycenter(self):
    x = 0
    y = 0
    for pt in self.points:
      x += pt[0]
      y += pt[1]
    n = len(self.points)
    return (x/n, y/n)



def computeGroupSurfaces(IR, groupDefs):
  groups = {}
  # group nodes by groups
  for node in IR:
    if 'cell' in node and 'tikz' in node and 'points' in node['tikz']:
      group = node['cell']['group']
      if group in groups:
        groups[group].append(node['tikz']['points'])
      else:
        groups[group] = [node['tikz']['points']]
    else:
      print("WARNING: skipping a node in computeGroupSurfaces")

  for group in groups:
    # find a closed path in the group of unsorted points, not always in the same order
    points = groups[group]
    # define starting point 
    path = points[0]
    search = path[-1]
    remaining = points[1:]
    while len(remaining) > 0:
      found = False
      for p in remaining:
        if search in p:
          found = True
          search = p[1-p.index(search)]
          path.append(search)
          remaining.remove(p)
          break
      if not found:
        print("ERROR: Unable to match next point at {} -- aborting".format(search))
        break

    if path[0] != path[-1]:
      # closed path can continue
      print("WARNING: not closed path")
      print(path)

    # should be a parameter...
    SCALE=2.0/117.3 # ~118pt/cm + 1/200 scale ie 1cm = 2m
    poly = Polygon(path, SCALE)
    surface = poly.getSurface()
    print("Group: {}: {} m2".format(groupDefs[group]['name'], surface)) 

    color = "blue"
    if groupDefs[group]['name'] == "enveloppe ext etage":
      IR.append({'tikz': poly.getTikz()})
      color = "red"
      poly.printIterativeDirections()

    for node in poly.getLengths(color):
      IR.append(node)



#################################
# MAIN: file processing
#################################
def main():

  parser = argparse.ArgumentParser(
    prog='svg2tikz',
    description='Convert Drawio-generated SVG files to Tikz Tex'
  )
  parser.add_argument('-c', '--config', required=False)
  # FIXME: add options properly to allow a simple "./svg2tikz input [output]" usage
  
  args = parser.parse_args()

  # config load FIXME: should use argparse
  if args.config:
    config.App.loadConf(args.config)
  else:
    print("Warning: using default config, including path to source and destination")

  conf = config.App.config()


  # INITIAL PARSING
  tree = xml.parse(conf['INPUT_FILE'])
  root = tree.getroot()
  # root format of drawio-generated svgs
  # {http://www.w3.org/2000/svg}defs    => (empty)
  # {http://www.w3.org/2000/svg}g       => (main group)
  # {http://www.w3.org/2000/svg}switch  => (disclaimer for edition without support of foreign object)
  main = root[1] # select the first group

  # MAIN PROCESSING
  print("[INFO] Parsing SVG file")
  IR = svgparser.processGroup(main)

  # Re-integrate infos from mxgraph if available
  if 'content' in root.attrib:
    print("[INFO] Attempting to parse original drawio mxfile")
    mxgraph = MxGraph()
    mxgraph.parseRaw(root.attrib['content'], App.outputFile('xml'))
    # align & annotate mxgraph with tikz/svg nodes
    mxgraph.annotate(IR)

    # pprint.pprint(IR)
    computeGroupSurfaces(IR, mxgraph.groups)
  else:
    print("[WARN] Cannot retrieve original drawio diagram source, overlay specs won't be matched.")



  print("[INFO] Starting tikz emission")
  tikz = emitter.emitTikz(IR)

  # OUTPUT FORMATTING
  tex = TIKZ_START() + '\n' + tikz + '\n' + TIKZ_END 

  if not conf['NO_COLOR_DEFS']:
    tex = '\n'.join(colors.getColorDefs()) + '\n' + tex
  if conf['STANDALONE_TEX']:
    if conf['STANDALONE_IS_BEAMER']:
      tex = '\documentclass{beamer}\n' + PREAMBLE + '\n\\begin{frame}\n' + tex + '\n\end{frame}\n' + FOOTER
    else:  
      tex = '\documentclass{standalone}\n' + PREAMBLE + '\n' + tex + '\n' + FOOTER

  # WRITE RESULT TO FILE
  with open(conf['OUTPUT_FILE'], 'w') as tikz:
    tikz.write(tex)


if __name__ == "__main__":
  main()