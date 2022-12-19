import re
from . import common

COLOR_RGB_REG = re.compile(r"\s*[rR][gG][bB]\(\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*\)\s*")
ColorDict={}
ColorDict['#ffffff'] = { 'name': 'white', 'custom': False, 'used': False}
ColorDict['#000000'] = { 'name': 'black', 'custom': False, 'used': False}

ColorDict['#00188d'] = { 'name': 'bad_ovh_darkblue', 'custom': True, 'used': False} 
ColorDict['#6881b3'] = { 'name': 'draw_darkblue1', 'custom': True, 'used': False} 
ColorDict['#cccccc'] = { 'name': 'draw_grey', 'custom': True, 'used': False} 
ColorDict['#36be0f'] = { 'name': 'green_phone', 'custom': True, 'used': False} 
ColorDict['#f56800'] = { 'name': 'orange_rss', 'custom': True, 'used': False} 

# should rather be included as independent SVGs ...
ColorDict['#282662'] = { 'name': 'apache_darkblue', 'custom': True, 'used': False} 
ColorDict['#7e2a7e'] = { 'name': 'apache_purple', 'custom': True, 'used': False} 
ColorDict['#c7203e'] = { 'name': 'apache_red', 'custom': True, 'used': False} 
ColorDict['#e46a2c'] = { 'name': 'apache_orange', 'custom': True, 'used': False} 
ColorDict['#f69825'] = { 'name': 'apache_yellow', 'custom': True, 'used': False} 
ColorDict['#205196'] = { 'name': 'stack_blue1', 'custom': True, 'used': False} 
ColorDict['#466ea8'] = { 'name': 'stack_blue1_flare', 'custom': True, 'used': False} 
ColorDict['#4385d4'] = { 'name': 'stack_blue2', 'custom': True, 'used': False} 
ColorDict['#1d6dcc'] = { 'name': 'stack_blue2_flare', 'custom': True, 'used': False} 
ColorDict['#36a4ee'] = { 'name': 'stack_blue3', 'custom': True, 'used': False} 
ColorDict['#58b3f1'] = { 'name': 'stack_blue3_flare', 'custom': True, 'used': False} 
ColorDict['#8ed5eb'] = { 'name': 'stack_blue4', 'custom': True, 'used': False} 

ColorDict['#c61914'] = { 'name': 'ovhDarkRed', 'custom': True, 'used': False}
ColorDict['#73e3ff'] = { 'name': 'ovhLightblue2', 'custom': True, 'used': False}
ColorDict['#ed743e'] = { 'name': 'ovhOrange', 'custom': True, 'used': False}
ColorDict['#a7d74d'] = { 'name': 'ovhGreen', 'custom': True, 'used': False}
ColorDict['#ffd224'] = { 'name': 'ovhYellow', 'custom': True, 'used': False}
ColorDict['#464649'] = { 'name': 'ovhDarkGrey', 'custom': True, 'used': False}
ColorDict['#d3d6dc'] = { 'name': 'ovhLightGrey', 'custom': True, 'used': False}
ColorDict['#0057f7'] = { 'name': 'ovhLightBlue', 'custom': True, 'used': False} 
ColorDict['#010c99'] = { 'name': 'ovhDarkBlue', 'custom': True, 'used': False} 
ColorDict['#c61914'] = { 'name': 'ovhDarkRed', 'custom': True, 'used': False}

ColorDict['#172942'] = { 'name': 'ugaBlueGrey', 'custom': True, 'used': False}
ColorDict['#ff4e02'] = { 'name': 'ugaOrange', 'custom': True, 'used': False}
ColorDict['#5f5f5f'] = { 'name': 'ugaLightGrey', 'custom': True, 'used': False}
ColorDict['#959595'] = { 'name': 'ugaLightGrey2', 'custom': True, 'used': False}

# ColorDict[""]
def getColor(colorString):
  if colorString[0] == '#':
    hexColor=colorString.lower()
  else:
    m = COLOR_RGB_REG.match(colorString)
    if m:
      hexColor = "#"
      for c in m.groups(): # not including complete match 0
        hexColor += '{:02X}'.format(common.getNiceNumber(c))
    else:
      print("Unable to parse color {}, defaulting to black".format(colorString))
      hexColor = "#000000"
    hexColor = hexColor.lower()
  # storage based on hexColor in all cases because simpler to use as a key
  if hexColor in ColorDict:
    ColorDict[hexColor]['used'] = True
    return ColorDict[hexColor]['name']
  else:
    cid = len(ColorDict)
    name = 'svg2tikz_c{}'.format(cid)
    ColorDict[hexColor] = {'name': name, 'custom': True, 'used': True}
    return name

def getColorDefs():
  res = []
  for key in ColorDict:
    elt = ColorDict[key]
    if elt['used'] and elt['custom']:
      r = int(key[1:3], 16)
      g = int(key[3:5], 16)
      b = int(key[5:7], 16)
      res.append("\\definecolor{{{}}}{{RGB}}{{{}, {}, {}}} %% {}".format(elt['name'], r, g, b, key))
  return res
