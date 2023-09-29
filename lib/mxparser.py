from pprint import pprint
import xml.etree.ElementTree as xml
import base64
import zlib
import urllib.parse

from .htmlparser import DrawHTMLParser
from .common import *
from .config import App


class MxGraph(object):

  groups = {} # the base type
  layers = {} # just pointer towards groups
  leaves = {} # id to index map (avoid copy of values)
  lst = [] # main linear storage

  def sanitizeTikzName(self, name):
    return name.replace('.', '_') # other to add ?

  def checkPoint(self, path, x, y):
    SHIFT_Y=-170
    SHIFT_X=574
    exp_tikz = "({},-{})".format(f(getNiceNumber(x)+SHIFT_X), f(getNiceNumber(y)+SHIFT_Y))
    print(exp_tikz)
    return exp_tikz in path

  def annotate(self, svg):
    print("[INFO] Starting tikz/mxgraph alignment & annotation")
    conf = App.config()
    shapes = conf['MXGRAPH_SHAPES']
    ignore_mxtext_newlines = conf['IGNORE_MXTEXT_NEWLINES']
    max_elt_for_txt_node = conf['MAX_ELT_FOR_TXT_NODE']

    svgIndex = 0
    mxNodeIndex = 0
    error = False
    for mxNode in self.lst:
      mxNodeIndex += 1
      if svgIndex >= len(svg):
        error = True
        print("[ERROR] svgIndex overflow -- processed {} mxNodes over {}".format(mxNodeIndex-1,len(self.lst)))
        break
      if mxNode['type'] == "leaf" and mxNode['visible']:

        svgNode = svg[svgIndex]['tikz']
        # basic alignment checking operations
        if 'sourcePoint' in mxNode['geometry'] and 'targetPoint' in mxNode['geometry']:
          if not 'draw' in svgNode['cmd']:
            print("[FAILED] expected draw command for source and target points")
            print(mxNode['geometry'])
            print(mxNode['id'])
            print(svgNode)
            print("---")
          else:
            src = mxNode['geometry']['sourcePoint']
            target = mxNode['geometry']['targetPoint']
            # issue: hard to check point, not the same scale ...

            # if not self.checkPoint(svgNode['path'], src['x'], src['y']):
            #   print("[FAILED] bad source point {} vs {}".format(svgNode['path'], src))
            # elif not self.checkPoint(svgNode['path'], target['x'], target['y']):
            #   print("[FAILED] bad source point {} vs {}".format(svgNode['path'], target))
            # else:
            #   print("[PASSED] - source & target matches")

        elif 'pos' in mxNode['geometry']:
          # typically mxgraph.shape... not sure what should be checked ...
          pass
        else:
          # relative geometry with very little information: nothing interesting to check
          pass 
          # print("relative geometry (not sure what to check ...)")
          # print(mxNode)

        # TODO: deal with shapes properly 
        # => needs further info = local dictionary (could be populated from sources of drawio itself)
        name = mxNode['id']
        length = 1
        if 'shape' in mxNode:
          name = mxNode['shape'] + '_' + name
          if mxNode['shape'] in shapes:
            length = shapes[mxNode['shape']] # not += but = 
          else:
            print("Unknown shape, please extend config: "+ mxNode['shape'])

        if 'image' in mxNode['style']:
          # print(mxNode['style']['image'])
          if mxNode['style']['image'] != False and '.' in mxNode['style']['image']:
            filename=mxNode['style']['image'].split('/')[-1]
            name = filename + '_' + name # FIXME: should use both name and id as separate attributes


        if 'endArrow' in mxNode['style'] and mxNode['style']['endArrow'] != "none":
          length += 1
        if 'orthogonalLoop' in mxNode['style'] and mxNode['style']['orthogonalLoop'] == "1":
          # older version of arrows ... not very precise though
          if not 'endArrow' in mxNode['style']:
            length += 1
        if 'startArrow' in mxNode['style'] and mxNode['style']['startArrow'] != "none":
          length += 1

        if mxNode['txt']: # node with value generate a second svg node
          # print(mxNode['id'])
          # print(mxNode['style'])
          # or not 'strokeColor' in mxNode['style'] => required in some weird cases....?
          hasStroke = 'strokeColor' in mxNode['style'] and mxNode['style']['strokeColor'] != "none"
          hasDraw = hasStroke or 'draw' in mxNode['style'] and mxNode['style']['draw'] != "none"
          hasFill = 'fillColor' in mxNode['style'] and mxNode['style']['fillColor'] != "none" 
          hasFill = hasFill or 'fill' in mxNode['style'] and mxNode['style']['fill'] != "none" 
          isIMG = 'image' in mxNode['style']
          isShape = 'shape' in mxNode['style'] and mxNode['style']['shape'] == 'step' 
          # isRect = 'shape' in mxNode['style'] and mxNode['style']['shape'] == 'rect'
          isHtml = False
          # isHtml = 'html' in mxNode['style'] and mxNode['style']['html'] == '1'
          isRect = False
          isDashed = False
          isDashed = 'dashed' in mxNode['style'] and mxNode['style']['dashed'] == '1'
          if hasDraw or hasFill or isIMG or isShape or isRect or isDashed or isHtml: 
            # should not be + one if only a text node 
            length += 1
          if not ignore_mxtext_newlines:
            # formatted text in drawio: splitted in separated svg nodes ....
            length += mxNode['txt'].count("\n")
          if max_elt_for_txt_node and length > max_elt_for_txt_node:
            print("Fixing length to {} for node {}".format(max_elt_for_txt_node, mxNode['id']))
            length = max_elt_for_txt_node

        # infos
        # print("Align: #{} {} -- {} ({})".format(svgIndex, svgNode['cmd'], mxNode['id'], length))

        # annotate all the corresponding nodes with  
        cell = {
          'id': mxNode['id'], 
          'group': mxNode['parent'], 
          'name': self.sanitizeTikzName(name),
          'overlays': mxNode['overlays']
        }
        applied = 0
        while applied < length:
          if svg[svgIndex]['tikz']['draw']: # skip empty nodes
            svg[svgIndex]['cell'] = cell
            applied += 1
          if applied == length and mxNode['txt']:
            if svg[svgIndex]['tikz']['cmd'] != "node":
              print("[ERROR] Expected text node here. {}".format(cell['id']))

          svgIndex += 1
          if svgIndex == len(svg) and applied < length:
            print("[ERROR] svgIndex overflow -- processed {} mxNodes over {}".format(mxNodeIndex-1,len(self.lst)))
            error = True
            break

    if svgIndex == len(svg) and not error:
      print("[SUCCESS] mxgraph aligned with tikz nodes: {}/{}".format(svgIndex, len(svg)))
    else:
      print("[ERROR] Misalignment of mxgraph with tikz nodes: {}/{} (pos / total)".format(svgIndex, len(svg)))



  def parseRaw(self, raw, xmlOutput = None ):
    diag = MxGraph.getEmbeddedDrawDiagram(raw, xmlOutput)
    self.parseMxDiagram(diag)


  @staticmethod
  def decodeDrawDiagram( raw ):
    b64decoded = base64.b64decode( raw )
    inflated = zlib.decompress(b64decoded , -15)
    return urllib.parse.unquote(inflated)

  @staticmethod
  def getEmbeddedDrawDiagram(content, xmlOutput=None):
    unquoted = urllib.parse.unquote(content)
    mxTree = xml.fromstring(unquoted)
    # only one child: either encoded diagram or raw diagram
    # for curious reason some newer versions does not seem to compress the diagram anymore ...?

    if not mxTree[0].text.strip() == '':
      diag = MxGraph.decodeDrawDiagram(mxTree[0].text)
      diagRoot = xml.fromstring(diag)
      mode = 'w'
    else:
      diagRoot = mxTree[0][0]
      diag = xml.tostring(diagRoot)
      mode = 'wb'

    if xmlOutput:
      with open(xmlOutput, mode) as f:
        f.write(diag)
        
    return diagRoot[0] # only one <root></root> container at root

  @staticmethod
  def parseMxArray(mxArray):
    res = []
    for child in mxArray:
      if child.tag != "mxPoint":
        print("ERROR: Unable to process mxGeometry point: {}".format(child.tag))
      elif 'x' in child.attrib and 'y' in child.attrib:
        res.append({'x': child.attrib['x'], 'y':child.attrib['y']})

    return res

  @staticmethod
  def parseMxGeometry(mxCell):
    res = {}
    for child in mxCell:
      if child.tag != "mxGeometry":
        print("ERROR: Unable to process mxCell geometry: {}".format(child.tag))
      else:
        if 'width' in child.attrib:
          res['width'] = child.attrib['width']  
        if 'height' in child.attrib:
          res['height'] = child.attrib['height']
        if 'x' in child.attrib and 'y' in child.attrib:
          res['pos'] = {'x': child.attrib['x'], 'y': child.attrib['y']}
        for point in child:
          match point.tag:
            case 'mxPoint':
              if 'x' in point.attrib and 'y' in point.attrib:
                res[point.attrib['as']] = {'x': point.attrib['x'], 'y': point.attrib['y']}
            case 'Array':
              res['control'] = MxGraph.parseMxArray(point)
            case others:
              print("ERROR: Unable to process mxGeometry point: {}".format(point.tag))
    return res

  # Investigation of mxgraph xml hierarchy
  # <mxCell id="0" />                   - root of the document (or page ?)
  # <mxCell id="1" parent="0" />        - default layer (named background)
  # Layers : <mxCell id="HuqE1C0zurAJJOl7Irtk-262" value="attack" parent="0" /> - style attribute is optional
  # Layers are ALWAYS parent="0", style is optional, visible="0" for hidden layers

  # Base for alignment:
  # use mxgraph as master
  # traverse mxgraph and increment a pointer on svg nodes  

  def parseMxDiagram(self, root):
    overlaySpecs = App.config()['OVERLAYS']
    for child in root:
      if child.tag != "mxCell":
        print("ERROR: Unable to process diagram element: {}".format(child.tag))
      elif child.attrib['id'] == "0":
        # skipping the 1 first root nodes
        pass
      else:
        mxCell = {}
        mxCell['id'] = child.attrib['id']
        mxCell['parent'] = child.attrib['parent']
        # print(child.attrib)
        style = child.attrib['style'] if 'style' in child.attrib else "" 

        ################### NEW LAYER ###################
        if child.attrib['parent'] == "0":
          # this is a custom layer
          visible = not 'visible' in child.attrib or child.attrib['visible'] != "0"
          if child.attrib['id'] == "1":
            # special case for default background layer
            name = 'default'
          else:
            name = child.attrib['value']
          specs = overlaySpecs[name] if name in overlaySpecs else ""
          print("Specs for {}: {}".format(name, specs))
          self.layers[name] = {
            'id': child.attrib['id'], 
            'style': style
          }
          self.groups[child.attrib['id']] = {
            'name': name,
            'parent': "0", 
            'children': [], 
            'overlays': specs, 
            'visible': visible, 
            'isLayer': True
            }
          mxCell['type'] = "layer"
          mxCell['overlays'] = specs
          # print("New layer: {} (visible: {}; style: {})".format(name, visible, style))

        else:
          # register child to its parent
          if not child.attrib['parent'] in self.groups:
            print("Error: detached leaf, unknown parent: {}".format(child.attrib['parent']))
            visible = False
            parent = self.groups['1'] # default group
          else:
            parent = self.groups[child.attrib['parent']]
            visible = parent['visible']
          parent['children'].append({'id': child.attrib['id'], 'nid':len(self.lst)})
          mxCell['visible'] = visible
          
          # inherit overlay specs
          specs = parent['overlays']
          if isinstance(specs, dict):
            if child.attrib['id'] in specs:
              specs = specs[child.attrib['id']]
            else:
              specs = specs['default']
          mxCell['overlays'] = specs
          
          ################### NEW GROUP ###################
          if child.attrib['style'][0:5] == "group":
            mxCell['type'] = "group"

            self.groups[child.attrib['id']] = {
              'parent': child.attrib['parent'], 
              'children': [], 
              'overlays': specs, # specs property is inherited from parent
              'visible': visible # visible property is inherited from parent
            }
            style = ""
          else:
            # print("mxCell {} with parent {}".format(child.attrib['id'], child.attrib['parent']))
            mxCell['type'] = "leaf"
            self.leaves[child.attrib['id']] = len(self.lst)

  
        # for conciseness
        if 'image=data:image/' in style:
          mxCell['style'] = {'image': "EMBEDDED IMAGE OMITTED FOR CONCISENESS"}
        else:
          styles = DrawHTMLParser.get_styles(style, '=')
          if 'shape' in styles:
            mxCell['shape'] = styles['shape']
          mxCell['style'] = styles
        mxCell['geometry'] = MxGraph.parseMxGeometry(child)
        if 'value' in child.attrib and child.attrib['value']: # must not be empty to be valid
          mxCell['txt'] = child.attrib['value']
        else:
          mxCell['txt'] = ""
        self.lst.append(mxCell)


