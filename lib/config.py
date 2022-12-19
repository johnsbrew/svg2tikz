#!/usr/bin/env python3

import os
import yaml

import collections.abc

class App:
  CURRENT_DIR="/Users/jbruant/syncOut/fpga-cifre/docs/slides/figures/svg2tikz/lib"
  DEFAULT_CONF = CURRENT_DIR + "/config_default.yml"

  __conf = None

  @staticmethod
  def __update_rec(d, u):
      for k, v in u.items():
          if isinstance(v, collections.abc.Mapping):
              if not k in d or d[k] == "":
                d[k] = {} 
              d[k] = App.__update_rec(d[k], v)
          else:
              d[k] = v
      return d

  @staticmethod
  def __update(conf):
    App.__update_rec(App.__conf, conf)


  @staticmethod
  def loadConf(configFile=None):
    if not App.__conf:
      # first load the default and then override with new values
      with open(App.DEFAULT_CONF, 'r') as file:
        App.__conf = yaml.safe_load(file)
    
    # update conf with new values 
    if configFile:
      print("Loading config file from {}".format(configFile))
      with open(configFile, 'r') as file:
        App.__update(yaml.safe_load(file))
    
    App.__conf['INPUT_FILE'] = App.__conf['INPUT_DIR'] + "/" + App.__conf['INPUT_FILENAME']
    App.__conf['OUTPUT_DEP_DIR'] = App.__conf['OUTPUT_DIR'] + "/" + App.__conf['DEP_DIR']
    App.__conf['OUTPUT_FILE'] = App.__conf['OUTPUT_DIR'] + "/" + App.__conf['OUTPUT_FILENAME']

    os.makedirs(App.__conf['OUTPUT_DEP_DIR'], exist_ok = True)
    App.__conf['INPUT_FILENAME_RAW'] = App.__conf['INPUT_FILENAME'][0:-(len(App.__conf['INPUT_FILENAME'].split('.')[-1])+1)]
  
  @staticmethod
  def outputFile(ext):
    return App.__conf['OUTPUT_DIR'] + "/" + App.__conf['INPUT_FILENAME_RAW'] + '.' + ext

  @staticmethod
  def config():
    if not App.__conf:
      App.loadConf()
    return App.__conf

