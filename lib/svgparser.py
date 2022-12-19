#!/usr/bin/env python3
import re
import os
import base64
from .common import *
from .font import *
from .colors import *
from .config import App
from .htmlparser import *

# subprocess required for external file extractions (asar to svg ; svg to pdf)
import subprocess
# external binary dependencies (must be available in path): 
# - svg2pdf
# port provides `which svg2pdf` => svg2pdf is provided by: librsvg
# can also be installed with brew install svg2pdf (based on cairo in both cases)
# - npx (Node CLI environment: <package_manager:brew|apt|...> install npm)
# NB: npx will automatically install locally asar (and its dependencies) in ~/.npm/_npx/ 

# TODO: check if those external binaries could be replaced with equivalent python packages?

def processRect(rect):
  startX = getNiceNumber(rect.attrib['x'])
  startY = getNiceNumber(rect.attrib['y'])
  stopX = startX + getNiceNumber(rect.attrib['width'])
  stopY = startY + getNiceNumber(rect.attrib['height'])

  tikz = getColoredDrawCommand(rect.attrib)
  
  if 'rx' in rect.attrib:
    radius = getNiceNumber(rect.attrib['rx'])
    tikz['opts']["rounded corners"] = "{}\pt".format(radius)
    if 'ry' in rect.attrib and rect.attrib['ry'] != rect.attrib['rx']:
      print("Got uneven radius for rectangle, using rx ({}), discarding ry ({})".format(rect.attrib['rx'], rect.attrib['ry']))
  
  # Y axis is inverted in SVG % TikZ
  tikz['path'] = "({}, -{}) rectangle ({}, -{})".format(f(startX), f(startY), f(stopX), f(stopY))
  tikz['content'] = {}
  return tikz



def processSwitch(switch):
  # {'pointer-events': 'none', 'width': '100%', 'height': '100%', 'requiredFeatures': 'http://www.w3.org/TR/SVG11/feature#Extensibility', 'style': 'overflow: visible; text-align: left;'}
  if switch[0].tag != '{http://www.w3.org/2000/svg}foreignObject':
    print("Unable to process switch first child, with tag: {}".format(switch[0].tag))

  tikz = processHTML(switch[0][0], [switch[0].attrib])
  svg = {'tag': 'switch/' + switch[0].tag, 'attrib': switch[0].attrib }
  return {'tikz': tikz, 'svg': svg}


def parseBuffer(buffer):
  # the only expected string for buffer is a valid number or a couple of valid numbers 
  splitted = buffer.split(',')
  res = []
  for e in splitted:
    res.append({'type': 'number', 'value':getNiceNumber(e)})
  return res


def tokenizePathString(txt):
  """ Goal of this function is to return a list of tokens from a path string
  """
  tokens = []
  buffer = ''
  for char in txt:
    if char.isspace():
      # only processing buffer after a space or at the end
      if buffer:
        tokens += parseBuffer(buffer)
        buffer = ''
    elif char.isalpha():
      tokens.append({'type': 'cmd', 'value': char})
    else:
      # expecting a number
      buffer += char

  if buffer:
    tokens += parseBuffer(buffer)
  
  return tokens


def getPathCmd(txt):
  tokens = tokenizePathString(txt)
  res = []
  index = 0
  while index < len(tokens):
    tok = tokens[index]
    match tok['type']:
      case 'cmd':
        # first retrieve points
        points = []
        index += 1
        while index < len(tokens) and tokens[index]['type'] == 'number':
          points.append(tokens[index]['value'])
          index += 1
        
        # then match command against supported types
        match tok['value']:
          case 'M':
            # Move to given (x,y) position (no draw from current)
            if len(points) == 2:
              res.append({'action': 'move', 'x': points[0], 'y': points[1]})
            else:
              print("Badly formed move command, got {} points while 2 were expected".format(len(points)))
          case 'L':
            # Draw line to given (x,y) position
            if len(points) == 2:
              res.append({'action': 'line', 'x': points[0], 'y': points[1]})
            else:
              print("Badly formed line draw command, got {} points while 2 were expected".format(len(points)))
          
          case 'C':
            # Draw double control points bezier curve to given (x,y) position
            if len(points) == 6:
              cubic = { 'action': 'cubic', 'x': points[4], 'y': points[5]}
              cubic['cx1'] = points[0]
              cubic['cy1'] = points[1]
              cubic['cx2'] = points[2]
              cubic['cy2'] = points[3]
              res.append(cubic)
            else:
              print("Badly formed cubic curve command, got {} points while 6 were expected".format(len(points)))
          
          case 'Q':
            # Draw single control point bezier curve to given (x,y) position
            if len(points) == 4:
              quadratic = { 'action': 'quadratic', 'x': points[2], 'y': points[3]}
              quadratic['cx'] = points[0]
              quadratic['cy'] = points[1]
              res.append(quadratic)
            else:
              print("Badly formed quadratic curve command, got {} points while 4 were expected".format(len(points)))
          case 'Z':
            # Close current draw, returning to first point of the path
            if len(points) == 0:
              res.append({'action': 'close'})
            else:
              print("Unexpected arguments after closing command, got {} points while none were expected".format(len(points)))

          case others:
            print("Unexpected svg command: " + tok['value'])
        #TODO: there is still a lot of work here 

      case others:
        print("Unexpected token type: " + tok['type'])
  return res

def joinQuadraticPaths(lst, preQuadraticCmd, strengthX, strengthY):
  # join 2 quadratic paths as a single cubic path
  q1 = lst[0]
  q2 = lst[1]
  if strengthX != 100 or strengthY != 100:
    prevX = preQuadraticCmd['x']
    prevY = preQuadraticCmd['y']
    q1['cx'] = prevX + (q1['cx']-prevX)*strengthX/100.0
    q1['cy'] = prevY + (q1['cy']-prevY)*strengthY/100.0

    q2['cx'] = q2['x'] + (q2['cx']-q2['x'])*strengthX/100.0
    q2['cy'] = q2['y'] + (q2['cy']-q2['y'])*strengthY/100.0

  return  " .. controls ({},-{}) and ({},-{}) .. ({},-{})".format(f(q1['cx']), f(q1['cy']), f(q2['cx']), f(q2['cy']), f(q2['x']), f(q2['y']))

def clearQuadraticBuffer(lst, preQuadraticCmd):
  if not lst:
    # nothing to do
    return ""
  conf = App.config()
  if conf['FORCE_Q_AS_C']:
    # this is the only place where the Q_STRENGTH modulation makes sense
    if conf['Q_AS_C_STRENGTH_PERCENT'] != 100 or conf['Q_AS_C_STRENGTH_PERCENT'] != 100:
      prevX = preQuadraticCmd['x']
      prevY = preQuadraticCmd['y']
      cx1 = prevX + (lst[0]['cx']-prevX)*conf['Q_AS_C_STRENGTH_PERCENT']/100.0
      cy1 = prevY + (lst[0]['cy']-prevY)*conf['Q_AS_C_STRENGTH_PERCENT']/100.0
      x = lst[0]['x']
      y = lst[0]['y']
      cx2 = x + (lst[0]['cx']-x)*conf['Q_AS_C_STRENGTH_PERCENT']/100.0
      cy2 = y + (lst[0]['cy']-y)*conf['Q_AS_C_STRENGTH_PERCENT']/100.0

      res = joinQuadraticPaths([{'cx':cx1, 'cy':cy1}, {'cx':cx2, 'cy':cy2, 'x': x, 'y': y}], preQuadraticCmd, 100, 100)
    else:
      res = joinQuadraticPaths(lst + lst, preQuadraticCmd, 100, 100)
    lst.clear()
    return res
  else:
    cmd = lst[0]
    lst.clear()
    return " .. controls ({},-{}) .. ({},-{})".format(f(cmd['cx']), f(cmd['cy']), f(cmd['x']), f(cmd['y']))

def cmdToPath(commands):
  # current expectations: must start with a move and continue with lines until a close (or not)
  paths = []
  points = [] # for tracing controls points
  current = ''
  started = False
  preQuadraticCmd = {}
  quadraticBuffer = []
  lastCmd = {}

  for cmd in commands:
    match cmd['action']:
      case 'move':
        if started:
          current += clearQuadraticBuffer(quadraticBuffer, preQuadraticCmd)
          paths.append(current)
          current = ''
        else:
          started = True
        current = "({},-{})".format(f(cmd['x']), f(cmd['y']))

      case 'line':
        if not started:
          print("Draw commands requires a first move to initialize the path")
        current += clearQuadraticBuffer(quadraticBuffer, preQuadraticCmd)
        current += " -- ({},-{})".format(f(cmd['x']), f(cmd['y']))

      case 'quadratic':
        if not started:
          print("Draw commands requires a first move to initialize the path")
        if App.config()['JOIN_QQ_AS_C']:
          quadraticBuffer.append(cmd)
          if len(quadraticBuffer) == 2:
            strengthX = App.config()['QQ_AS_C_STRENGTH_PERCENT_X']
            strengthY = App.config()['QQ_AS_C_STRENGTH_PERCENT_Y']
            current += joinQuadraticPaths(quadraticBuffer, preQuadraticCmd, strengthX, strengthY)
            quadraticBuffer.clear()
          else:
            preQuadraticCmd = lastCmd
        else:
          current += " .. controls ({},-{}) .. ({},-{})".format(f(cmd['cx']), f(cmd['cy']), f(cmd['x']), f(cmd['y']))

        if App.config()['DISPLAY_CONTROL_POINTS']:
          points.append("\\node[shape=circle, draw=green, fill=green] at ({},-{}) {{}};".format( f(cmd['cx']), f(cmd['cy'])))

      case 'cubic':
        if not started:
          print("Draw commands requires a first move to initialize the path")
        current += clearQuadraticBuffer(quadraticBuffer, preQuadraticCmd)
        current += " .. controls ({},-{}) and ({},-{}) .. ({},-{})".format(f(cmd['cx1']), f(cmd['cy1']), f(cmd['cx2']), f(cmd['cy2']), f(cmd['x']), f(cmd['y']))
        if App.config()['DISPLAY_CONTROL_POINTS']:
          points.append("\\node[shape=circle, draw=orange, fill=orange] at ({},-{}) {{}};".format( f(cmd['cx1']), f(cmd['cy1'])))          
          points.append("\\node[shape=circle, draw=orange, fill=orange] at ({},-{}) {{}};".format( f(cmd['cx2']), f(cmd['cy2'])))

      case 'close':
        if not started:
          print("Warning: attempting to close a path without previous points")
        current += clearQuadraticBuffer(quadraticBuffer, preQuadraticCmd)
        started = False
        current += ' -- cycle'
        paths.append(current)
        current = ''

      case others:
        current += clearQuadraticBuffer(quadraticBuffer, preQuadraticCmd)
        print("TODO: {}".format(cmd['action']))
    lastCmd = cmd
  
  current += clearQuadraticBuffer(quadraticBuffer, preQuadraticCmd)
  if started:
    paths.append(current)

  return (paths, points)

def getColoredDrawCommand(attrib):
  tikz = {
    'draw': True,
    'cmd': '', 
    'opts': {}, 
  }
  opts = {}
  if 'stroke-width' in attrib:
    width = getNiceNumber(attrib['stroke-width'])
  else:
    width = 1
  opts['line width'] = '{}\pt'.format(width)

  if 'stroke-opacity' in attrib:
    if 'fill-opacity' in attrib:
      if attrib['stroke-opacity'] == attrib['fill-opacity']:
        opts['opacity'] = attrib['fill-opacity']
      else:
        opts['fill opacity'] = attrib['fill-opacity']
        opts['draw opacity'] = attrib['stroke-opacity']
    else:
      opts['draw opacity'] = attrib['stroke-opacity']
  elif 'fill-opacity' in attrib:
    opts['fill opacity'] = attrib['fill-opacity']

  if 'stroke-dasharray' in attrib:
    dashpattern =attrib['stroke-dasharray']
    m = re.match(r"([0-9.]+)[ ,]([0-9.]+)", dashpattern)
    if m:
      opts['dash pattern'] = 'on {}\\pt off {}\\pt'.format(m.group(1), m.group(2))
    else:
      print("Unable to parse dash pattern: {}".format())

  if attrib['stroke'] != 'none' and attrib['fill'] == 'none':
    opts['color'] =  getColor(attrib['stroke'])
    tikz['cmd'] = 'draw'
  elif attrib['stroke'] == 'none' and attrib['fill'] != 'none':
    opts['color'] =  getColor(attrib['fill'])
    tikz['cmd'] = 'fill'
    del opts['line width']
    if 'dash pattern' in opts:
      del opts['dash pattern']
  elif attrib['stroke'] != 'none' and attrib['fill'] != 'none':
    opts['draw'] =  getColor(attrib['stroke'])
    opts['fill'] =  getColor(attrib['fill'])
    tikz['cmd'] = 'filldraw'
  else:
    tikz['draw'] = False
    opts['color'] = 'black'
    tikz['cmd'] = 'draw'

  tikz['opts'] = opts
  return tikz

PARSE_ROTATE=re.compile(r"rotate\(([-0-9.]+)[, ]([-0-9.]+)[, ]([-0-9.]+)\)")
PARSE_TRANSLATE=re.compile(r"translate\(([-0-9.]+)[, ]([-0-9.]+)\)")
def getTransforms(transform):
  # rotate(-90,722.86,99.03) becomes:
  # - rotation direction is inverted ; y axis is inverted
  # \begin{scope} [rotate around={90:((722.86,-99.03))}]
  # FIXME: does not guarantee transform order => could be an issue for shift + rotate
  transforms={}
  tfs = transform.split(')')
  for tf in tfs:
    if tf == '':
      break
    tf = tf+')'
    rotate = PARSE_ROTATE.match(tf)
    if rotate:
      angle = getNiceNumber(rotate.group(1)) * -1
      x = getNiceNumber(rotate.group(2))
      y = getNiceNumber(rotate.group(3)) * -1
      transforms["rotate around"] = "{{{}:(({},{}))}}".format(angle, x, y)
      transforms["rotate"] = angle
    else:
      translate = PARSE_TRANSLATE.match(tf)
      if translate:
        x = getNiceNumber(translate.group(1))
        y = getNiceNumber(translate.group(2)) * -1
        transforms["shift"] = "{{({},{})}}".format(x, y)
      else:
        print("[WARN] Ignored transform: {}".format(tf))
  
  if not transforms:
    print("Unable to parse transform: {}".format(transform))

  return transforms

def processPath(path):

  commands = getPathCmd(path.attrib['d'])
  # potentially multiple traces per paths 
  (traces, points) = cmdToPath(commands)
  tikz = getColoredDrawCommand(path.attrib)

  if not tikz['draw']:
    print("Unexpected transparent path, drawn as black path")
  
  # https://texample.net/tikz/examples/set-operations-illustrated-with-venn-diagrams/
  # FINAL explanation: tikz works exactly as SVG :D
  # both XOR path fill by default within the same command
  tikz['path'] = '\n'.join(traces)

  if App.config()['DISPLAY_CONTROL_POINTS']:
    tikz['extra'] = points

  if 'transform' in path.attrib:
    tikz['transforms'] = getTransforms(path.attrib['transform'])

  tikz['content'] = {}


  return tikz


def processEllipse(ellipse):
  # <ellipse cx="782" cy="491.5" rx="4" ry="4" fill="#ffffff" stroke="none" pointer-events="all" />
  #  \draw (0,0) ellipse (2cm and 1cm);

  tikz = getColoredDrawCommand(ellipse.attrib)
  if not tikz['draw']:
    print("Note: transparent ellipse drawn as black path")
  
  x = getNiceNumber(ellipse.attrib['cx'])
  y = getNiceNumber(ellipse.attrib['cy'])
  rx = getNiceNumber(ellipse.attrib['rx'])
  ry = getNiceNumber(ellipse.attrib['ry'])
  # NB: \pt are not required here because the node will be scaled automatically
  tikz['path'] = "({},-{}) ellipse ({}pt and {}pt)".format(f(x), f(y), f(rx), f(ry))
  if 'transform' in ellipse.attrib:
    tikz['transform'] = getTransforms(ellipse.attrib['transform'])
  return tikz


def retrieveSVGfromASAR(path):
  paths = path.split(".asar/")
  asarFile = paths[0] + ".asar"
  targetFile = paths[1]
  fileName = targetFile.split('/')[-1]
  filePath = App.config()['OUTPUT_DEP_DIR'] + "/" + fileName

  print("Extracting {} from local asar archive".format(fileName))

  proc = subprocess.run(["npx", "--yes", "asar", "ef", asarFile, targetFile], 
    stdout=subprocess.DEVNULL, cwd = App.config()['OUTPUT_DEP_DIR'])
  code = proc.returncode
  if code != 0:
    print("Unexpected error {} with asar file extraction, is npm installed and visible in path?".format(code))

  return filePath

def svg2pdf(svg, pdf):
  print("Converting {} to pdf".format(svg))
  proc = subprocess.run(["svg2pdf", svg, pdf], stdout=subprocess.DEVNULL)
  code = proc.returncode
  if code != 0:
    print("Unexpected error {} with svg2pdf conversion, is svg2pdf installed and visible in path?".format(code))

def getIncludeGraphics(path):
  ext = path.split('.')[-1]
  filename = path.split('/')[-1]
  rawfilename = filename[0:-(len(ext)+1)]
  match ext:
    case 'svg':
      pdfFile =  rawfilename + '.pdf'
      pdfPath = App.config()['OUTPUT_DEP_DIR'] + '/' + pdfFile
      svg2pdf(path, pdfPath)
      return App.config()['DEP_DIR'] + '/' + pdfFile

    case 'png':
      return App.config()['DEP_DIR'] + '/' + filename

    case others:
      print("Unable to provide valid format for given embedded image: {}".format(path))
      return "INVALID EMBEDDED IMAGE"

RESOURCE_CACHE = {}
EMBEDDED_COUNT = []
HREF='{http://www.w3.org/1999/xlink}href'
def processImage(img):
  # 'x': '569.5', 'y': '208.5', 'width': '50', 'height': '50', '{http://www.w3.org/1999/xlink}href':
  tikz = {
    'draw': False, # False to preserve empty containers in the IR
    'cmd': 'node', 
    'opts': {},
    'path': '',
    'content': {
      'value': ''
    }, 
    'extra': [],
    'transforms': {}
  }
  if not HREF in img.attrib:
    print("Expected resource link for image")
    return tikz

  rsc = img.attrib[HREF]
  if rsc in RESOURCE_CACHE:
    includePath = RESOURCE_CACHE[rsc]

  elif len(rsc) > 8 and rsc[0:8] == 'file:///':
    # local file, need the first / => absolute path
    path = rsc[7:]
    filename = path.split('/')[-1]
    expected = App.config()['OUTPUT_DEP_DIR'] + '/' + filename
    if not App.config()['FORCE_NEW_EXTRACTION'] and os.path.exists(expected):
      # check if image is present by name
      print("INFO: skipping extraction of {}".format(expected))
      extracted = expected
    elif '.asar/' in path:
      extracted = retrieveSVGfromASAR(path)
    else:
      # must at least copy the file locally, or directly convert to pdf if required ?
      print("TODO: not within asar file - need to copy file")
      extracted = expected
    
    includePath = getIncludeGraphics(extracted)
    RESOURCE_CACHE[rsc] = includePath


  elif len(rsc) > 10 and rsc[0:10] == 'data:image':
    data = rsc[10:]
    if len(data) > 15 and data[0:15] == '/svg+xml;base64':
      raw = data[15:]
      # goal: decode base 64, store to file and convert to pdf for includegraphics
      
      svgFile = '{}_embedded_{}.svg'.format(App.config()['INPUT_FILENAME_RAW'], len(EMBEDDED_COUNT))
      svgPath = App.config()['OUTPUT_DEP_DIR'] + '/' + svgFile
      with open(svgPath, 'wb') as svg:
        svg.write(base64.b64decode( raw ))
      
      includePath = getIncludeGraphics(svgPath)
      EMBEDDED_COUNT.append(includePath)
      RESOURCE_CACHE[rsc] = includePath

    elif len(data) > 11 and data[0:11] == '/png;base64':
      raw = data[11:]
      pngFile = '{}_embedded_{}.png'.format(App.config()['INPUT_FILENAME_RAW'], len(EMBEDDED_COUNT))
      pngPath = App.config()['OUTPUT_DEP_DIR'] + '/' + pngFile
      with open(pngPath, 'wb') as png:
        png.write(base64.b64decode( raw ))
      
      includePath = getIncludeGraphics(pngPath)
      EMBEDDED_COUNT.append(includePath)
      RESOURCE_CACHE[rsc] = includePath
      pass
    else: 
      print('Unable to parse image {}'.format(rsc[0:100]))
      return tikz
  else:
    print("Unable to parse image format: {}".format(rsc[0:100]))
    return tikz

  # based on the resulting includePath + img.attrib, draw the full node
  xAnchor = getNiceNumber(img.attrib['x'])
  yAnchor = getNiceNumber(img.attrib['y'])
  w = getNiceNumber(img.attrib['width'])
  h = getNiceNumber(img.attrib['height'])

  x = xAnchor + w/2
  y = yAnchor + h/2
  # \pt are not required here: the node will be scaled automatically
  tikz['content']['value'] = "\\includegraphics[width={}pt, height={}pt]{{{}}}".format(f(w),f(h),includePath)
  tikz['path'] = "at ({},-{})".format(f(x), f(y))
  tikz['draw'] = True
  if 'opacity' in img.attrib:
    tikz['opts']['opacity'] = img.attrib['opacity']
  return tikz

def processSVGText(txt, attrib):
  # <g fill="#FFFFFF" font-family="Helvetica" font-weight="bold" pointer-events="none" text-anchor="middle" font-size="18px"><text x="655.96" y="569">VAC</text></g>
  tikz = {
    'draw': True, # False to preserve empty containers in the IR
    'cmd': 'node', 
    'opts': {},
    'path': '',
    'content': {
      'value': txt.text
    }, 
    'extra': [],
    'transforms': {}
  }

  xAnchor = getNiceNumber(txt.attrib['x'])
  yAnchor = getNiceNumber(txt.attrib['y'])
  # yAnchor = attr['padding-top'] + height / 2 * (1 + txt.count("\\") / 2)
  # fill="#FFFFFF" font-family="Helvetica" font-weight="bold" text-anchor="middle" font-size="18px"
  opts = {}
  opts["align"]='center' # required for multiple lines
  if 'fill' in attrib:
    opts["color"] = getColor(attrib['fill'])
  
  if 'text-anchor' in attrib:
    match attrib['text-anchor']:
      case 'middle': 
        anchor = 'center'
      case others:
        print("WARN: unsupported text-anchor {}".format(others))
        anchor = others 
    opts["anchor"] = anchor

  font = []
  if 'font-weight' in attrib and attrib['font-weight'] == "bold":
    font.append('\\bf')

  if 'font-size' in attrib and attrib['font-size'][-2:] == "px":
    size = getNiceNumber(attrib['font-size'][0:-2])
    yAnchor = yAnchor + size / 2 * (txt.text.count("\\") / 2 - 0.8)
    cmd = getFontSizeCmd(size)
    if cmd:
      font.append(cmd)

  if font:
    opts["font"] = ''.join(font)

  tikz['path'] = "at ({},-{})".format(f(xAnchor), f(yAnchor))
  tikz['opts'] = opts
  return tikz

def processGroup(group):
  res = []

  for child in group:
    svg = {'tag': child.tag[28:], 'attrib': child.attrib}
    match child.tag:
      # does not seem very resilient ? is this particular xmlns required? 
      case '{http://www.w3.org/2000/svg}g': 
        res += processGroup(child)

      case '{http://www.w3.org/2000/svg}rect':
        res.append({'tikz': processRect(child), 'svg': svg})

      case '{http://www.w3.org/2000/svg}path':
        res.append({'tikz': processPath(child), 'svg': svg})

      case '{http://www.w3.org/2000/svg}switch':
        res.append(processSwitch(child))

      case '{http://www.w3.org/2000/svg}ellipse':
        res.append({'tikz': processEllipse(child), 'svg': svg})

      case '{http://www.w3.org/2000/svg}image':
        res.append({'tikz': processImage(child), 'svg': svg})

      case '{http://www.w3.org/2000/svg}text':
        res.append({'tikz': processSVGText(child, group.attrib), 'svg': svg})

      case other:
        print("Cannot process :" + child.tag)
  
  if 'transform' in group.attrib:
    # print("Found some transform for current group: {}".format(group.attrib['transform']))
    for r in res:
      r['tikz']['transforms'] = getTransforms(group.attrib['transform'])
    
  if 'opacity' in group.attrib:
    for r in res:
      r['tikz']['opts']['opacity'] = group.attrib['opacity']

  return res
