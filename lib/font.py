

# Command             10pt    11pt    12pt
# \tiny               5       6       6
# \scriptsize         7       8       8
# \footnotesize       8       9       10
# \small              9       10      10.95
# \normalsize         10      10.95   12
# \large              12      12      14.4
# \Large              14.4    14.4    17.28
# \LARGE              17.28   17.28   20.74
# \huge               20.74   20.74   24.88
# \Huge               24.88   24.88   24.88

# POINT_SIZE_DEFAULT_TEX=11
# POINT_SIZE_DEFAULT_SVG=12

AVAILABLE_PT = [6, 8, 9, 10, 11, 12, 15, 16, 21, 25]
PT_TO_CMD = [
  "\\tiny", # 6
  "\\scriptsize", # 8
  "\\footnotesize", # 9
  "\\small", # 10
  "\\normalsize", # 11
  "\\large", # 12
  "\\Large", # 15
  "\\LARGE", # 17
  "\\huge", # 21
  "\\Huge" # 25
]

def getFontSizeCmd(pt):
  # the idea here is NOT to get a perfect ratio but use the default command for usable result 
  if pt in AVAILABLE_PT:
    cmd = PT_TO_CMD[AVAILABLE_PT.index(pt)]
  elif pt > AVAILABLE_PT[-1]:
    return "\\fontsize{{{}}}{{{}}}\\selectfont".format(pt,pt)
  else:
    cmd = PT_TO_CMD[0]
    index = 0
    for defaultpt in AVAILABLE_PT:
      if pt >= defaultpt:
        cmd = PT_TO_CMD[index]
        index += 1
      else:
        break
  if cmd == "\\normalsize":
    return ""
  else:
    return cmd

def getFontSize(pt):
  cmd = getFontSizeCmd(pt)
  if cmd == "":
    return ""
  else:
    return ",font={}".format(cmd)


FONT_FAMILY_MAP = {
  "Courier New": "\\ttfamily",
  "Helvetica": "\\normalfont",
  "arial": "\\normalfont"
}

def getFontFamilyCmd(font):
  font = font.strip('"')
  style = "\\normalfont"
  if font in FONT_FAMILY_MAP:
    style = FONT_FAMILY_MAP[font]

  if style == "\\normalfont":
    return ""
  return style


FONT_WEIGHT_MAP = {
  "normal": "\\mdseries",
  "bold": "\\bfseries"
}

def getFontWeightCmd(weight):
  if weight in FONT_WEIGHT_MAP:
    return FONT_WEIGHT_MAP[weight]
  print("Unknown font-weight {}".format(weight))