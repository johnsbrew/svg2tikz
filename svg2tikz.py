#!/usr/bin/env python3

import pprint
import xml.etree.ElementTree as xml
import argparse

from lib import config,svgparser,colors,emitter
from lib.defs import *
from lib.mxparser import MxGraph

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
  # TODO: make this part useful
  if 'content' in root.attrib:
    print("[INFO] Attempting to parse original drawio mxfile")
    mxgraph = MxGraph()
    mxgraph.parseRaw(root.attrib['content'], App.outputFile('xml'))
    # align & annotate mxgraph with tikz/svg nodes
    # (WIP)
    mxgraph.annotate(IR)
  else:
    print("[WARN] Cannot retrieve original drawio diagram source, overlay specs won't be matched.")

  print("[INFO] Starting tikz emission")
  tikz = emitter.emitTikz(IR)

  # OUTPUT FORMATTING
  tex = TIKZ_START() + '\n' + tikz + '\n' + TIKZ_END 

  if not conf['NO_COLOR_DEFS']:
    tex = '\n'.join(colors.getColorDefs()) + '\n' + tex
  if conf['STANDALONE_TEX']:
    tex = PREAMBLE + '\n' + tex + '\n' + FOOTER

  # WRITE RESULT TO FILE
  with open(conf['OUTPUT_FILE'], 'w') as tikz:
    tikz.write(tex)


if __name__ == "__main__":
  main()