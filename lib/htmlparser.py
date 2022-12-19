import xml.etree.ElementTree as xml
from html.parser import HTMLParser

from .colors import *
from .common import *
from .font import *
from .config import App



class DrawHTMLParser(HTMLParser):
  __res = []
  
  @staticmethod
  def get_styles(styles_str, sep=':'):
    res = {}
    if not styles_str:
      return res
    styles = styles_str.strip(';').split(';')
    for style in styles:
      if sep in style:
        kv = style.split(sep)
        key = kv[0].strip()
        value = kv[1].strip()
        res[key] = value
      else:
        res[style] = True
    return res

  __style = {}
  def update_style(self, attrib):
    if 'style' in attrib and 'text-align' in attrib['style']:
      styles = DrawHTMLParser.get_styles(attrib['style'])
      self.__style['text-align'] = styles['text-align']


    if 'style' in attrib and ('margin-left' in attrib['style'] or 'line-height' in attrib['style']):
      # then attempt to parse CSS stylesheet
      # remove trailing semicolon to avoid last empty entry after split
      styles = DrawHTMLParser.get_styles(attrib['style'])
      for key in styles:
        value = styles[key]
        if len(value) > 2 and value[-2:] == "px":
          value = getNiceNumber(value[0:-2])
        else:
          try:
            value = getNiceNumber(value)
          except:
            pass
        self.__style[key] = value


  def handle_font(self, attrib):
    self.handle_inline(attrib)

  # inline scopes (cannot be breaked trivially to produce the expected output)
  __scopes = []
  # allowbr indicates if the scope must be closed and re-opened to handle a line break
  # header string will be appended after a line break
  def open_scope(self, pre="", header= "", fontscale=1):
    self.__scopes.append({'pre':pre, 'header':header, 'fontscale':fontscale})
    if pre != '' or header != '':
      self.__res.append("{}{{{}".format(pre, header))

  # __early_closed_scope = False
  def close_scope(self):
    if self.__scopes:
      scope = self.__scopes.pop()
      if scope['pre'] != '' or scope['header'] != '':
        self.__res.append("}")

  __pending_br = ""
  def check_pending_br(self):
    if self.__pending_br:
      self.__res.append(self.__pending_br)
      self.__pending_br = ""

  def insert_line_break_in_scopes(self, height):
    self.check_pending_br()
    # height is the current line width
    # it will be corrected depending on current scopes (in particular font-size)
    reopen_scopes_str = []
    reopen_scopes = []
    fontscale = 1
    potential_res = []
    for scope in self.__scopes:
      reopen_scopes.append(scope)
      if scope['pre'] != "" or scope['header'] != "":
        potential_res.append("}")
        reopen_scopes_str.append("{}{{{}".format(scope['pre'], scope['header']))
      fontscale = fontscale * scope['fontscale']

    # FIXME: 12 as default might have curious side-effects? 
    if self.__current_line_max_fontsize != 12:
      scale = ((self.__current_line_max_fontsize / 12.0) - 1) * 0.2
    elif fontscale != 1:
      scale = fontscale
    else:
      scale = height
    if scale == 1:
      potential_res.append("\\\\")
    else:
      potential_res.append("\\\\[{}em]".format(f(scale)))

    potential_res.append("".join(reopen_scopes_str))
    self.__pending_br = "".join(potential_res)
    # self.__res.append("".join(potential_res))
    self.__scopes.clear()
    self.__scopes += reopen_scopes

  __last_was_command = False
  __current_line_max_fontsize = 12
  def handle_inline(self, attrib, noscope = False):

    if 'style' in attrib:
      attrib |= DrawHTMLParser.get_styles(attrib['style'])
      del attrib['style']
    res = []
    fontscale = 1
    for style in attrib:
      match style:
        case 'color':
          res.append("\\color{{{}}}".format(getColor(attrib['color'])))
        case 'font-size':
          size = getNiceNumber(attrib['font-size'][0:-2])
          fontscale = size / 12.0
          self.__current_line_max_fontsize = max(size, self.__current_line_max_fontsize)
          cmd = getFontSizeCmd(size) # not a pre-parsed CSS attrib
          if cmd:
            res.append(cmd)
            self.__last_was_command = True
        case 'face':
          cmd = getFontFamilyCmd(attrib['face'])
          if cmd:
            res.append(cmd)
            self.__last_was_command = True
        case 'font-weight':
          cmd = getFontWeightCmd(attrib['font-weight'])
          if cmd:
            res.append(cmd)
            self.__last_was_command = True
            
        case others:
          print("TODO: unsupported attribute for inline html tag {}".format(others))
    
    res = "".join(res)
    if not noscope:
      self.open_scope(header=res, fontscale = fontscale)
    else:
      self.__pending_br += res
      # self.__res.append(res)

  def handle_br(self, attrib):
    # might cause issues with the stacked defs ???
    # reason: cannot terminate a line within a scope
    if 'line-height' in self.__style and self.__style['line-height'] != 1:
      scale = (self.__style['line-height'] - 1 ) * 0.60
      # if 'font-family' in self.__style:
      #   if getFontFamilyCmd(self.__style['font-family']):
      #     scale = scale * 0.60
      #   else:
      #     scale = scale * 0.60

      self.insert_line_break_in_scopes(scale)
    else:
      self.insert_line_break_in_scopes(1)
    
    self.__current_line_max_fontsize = 12 # reset after line break
    if attrib:
      self.handle_inline(attrib, noscope=True)

  def handle_b(self, attrib):
    self.open_scope(header="\\bfseries ")

  def handle_i(self, attrib):
    self.open_scope(header="\\itshape ")
    
  def handle_span(self, attrib):
    self.handle_inline(attrib)
  
  __seen_content_since_last_div = False
  def handle_div(self, attrib):
    if self.__seen_content_since_last_div:
      self.handle_br({})
    self.__seen_content_since_last_div = False
    if 'style' in attrib:
      self.update_style(attrib)
      # print(self.__style) 

  def handle_p(self, attrib):
    if 'style' in attrib:
      self.update_style(attrib)
      # print(self.__style)


  def handle_starttag(self, tag, attrs):
    attrib = dict(attrs)
    self.check_pending_br()
    match tag:
      case 'html:font':
        self.handle_font(attrib)
      case 'html:br':
        self.handle_br(attrib)
      case 'html:b':
        self.handle_b(attrib)
      case 'html:i':
        self.handle_i(attrib)
      case 'html:span':
        self.handle_span(attrib)
      case 'html:div':
        self.handle_div(attrib)
      case 'html:p':
        self.handle_p(attrib)
      case others:
        print("TODO: Unsupported tag: {}".format(others))


  def handle_endtag(self, tag):
    match tag:
      case 'html:font':
        self.close_scope()
      case 'html:br':
        pass
      case 'html:b':
        self.close_scope()
      case 'html:i':
        self.close_scope()
      case 'html:span':
        self.close_scope()
      case 'html:div':
        self.__pending_br = ""
      case 'html:p':
        pass
      case others:
        print("TODO: Unsupported tag: {}".format(others))
  
  def handle_data(self, data):
    self.check_pending_br()
    # Avoid continuation of a command with a string
    if self.__last_was_command and data[0] != " ":
      self.__res.append(" ")
    self.__last_was_command = False

    self.__seen_content_since_last_div = True
    # probably other chars to manage ?
    clean = data.replace("_", "\\_")
    clean = clean.replace("{", "\\string{")
    clean = clean.replace("}", "\\string}")
    clean = clean.replace("&", "\\&")
    clean = clean.replace("^", "\\^")
    clean = clean.replace("#", "\\#")
    self.__res.append(clean)

  def reset(self) -> None:
    self.__res.clear()
    self.__style.clear()
    return super().reset()

  def getTikz(self):
    return (''.join(self.__res), self.__style)

def processHTML(html, attrib):
  parser = DrawHTMLParser()
  raw = xml.tostring(html).decode("utf-8")
  # print(attrib)
  # [{'pointer-events': 'none', 'width': '100%', 'height': '100%', 'requiredFeatures': 'http://www.w3.org/TR/SVG11/feature#Extensibility', 'style': 'overflow: visible; text-align: left;'}]
  parser.feed(raw)
  (txt, attr) = parser.getTikz()
  
  # Remove trailing <br>
  split = txt.split("\\\\")
  if split[-1] == '':
    txt = txt[:-2] 
  elif split[-1][-3:] == "em]" and split[-1][0] == '[':
    txt = txt[:-(len(split[-1])+2)]

  res = processText(txt, attr)
  parser.reset()
  return res


def processText(txt, attr):

  tikz = {
    'draw': True,
    'cmd': 'node', 
    'content': {'value': txt, 'styles': attr},
  }

  points = []
  points.append("\\node[shape=circle, draw=green, fill=green] at ({},-{}) {{}};".format( f(attr['margin-left']), f(attr['padding-top'])))

  yAnchor = attr['padding-top']
  if 'align-items' in attr:
    #  align-items: unsafe center;
    #  align-items: unsafe flex-start;
    values = attr['align-items'].split(' ')
    if 'flex-start' in values:
      height = attr['font-size'] * attr['line-height']
      yAnchor = attr['padding-top'] + height / 2 * (1 + txt.count("\\\\") * 1.08)
  else:
    print(attr)
  
  opts={} 
  xAnchor = attr['margin-left']
  if attr['width'] != 1:
    points.append("\\node[shape=circle, draw=green, fill=green] at ({},-{}) {{}};".format( f(attr['margin-left'] + attr['width']), f(attr['padding-top'])))

  if 'text-align' in attr:
    opts["align"] = attr['text-align']
    if txt.count("\\\\"):
      opts["line width"] = "{}pt".format(f(attr['width'])) # do NOT use \pt => destroy line break 
    else:
      # text width is unfortunately unable to handle \\[X.Xem] (and cannot use both)
      if attr['width'] != 1:
        opts["text width"] = "{}pt".format(f(attr['width'])) # do NOT use \pt => destroy line break 
    match attr['text-align']:
      case 'left':
        xAnchor = attr['margin-left']
        opts['anchor'] = 'west'
        opts['inner sep'] = '1mm'
        opts['outer sep'] = '0mm'
      case 'center':
        xAnchor = attr['margin-left'] + attr['width'] / 2

      case 'right':
        xAnchor = attr['margin-left'] + attr['width']
        opts['anchor'] = 'east'

      case others:
        print("Error unable to process text-align {}".format(others))
  else:
    opts["line width"] = "{}pt".format(f(attr['width'])) # do NOT use \pt => destroy line break 
    opts["align"] = "center" # required for multiple lines
    xAnchor = attr['margin-left'] + attr['width'] / 2

  tikz['path'] = "at ({},-{})".format(f(xAnchor), f(yAnchor))
  points.append("\\node[shape=circle, draw=orange, fill=orange] at ({},-{}) {{}};".format( f(xAnchor), f(yAnchor)))

  if 'color' in attr:
    opts["color"] = getColor(attr['color'])

  font = []
  if 'font-weight' in attr and attr['font-weight'] == "bold":
    font.append('\\bfseries')

  if 'font-style' in attr and attr['font-style'] == "italic":
    font.append('\\itshape')

  if 'font-size' in attr:
    cmd = getFontSizeCmd(attr['font-size'])
    if cmd:
      font.append(cmd)

  if 'font-family' in attr:
    cmd = getFontFamilyCmd(attr['font-family'])
    if cmd:
      font.append(cmd)

  if font:
    opts["font"] = ''.join(font)

  tikz['opts'] = opts

  if App.config()['DISPLAY_TXT_ANCHOR']:
    tikz['extra'] = points
  return tikz

