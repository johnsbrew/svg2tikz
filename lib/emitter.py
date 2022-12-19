# expected return format of svgparser
# NB: a better structure would separate svg parsing & conversion but it is not required here
# we only separate final emission to allow insertion of information from mxgraph
IR_FMT = [
  {
    'cell': {  # will be filled by mxgraph
      'id': 'str', 
      'group': 'str', 
      # more to be defined
    },
    'tikz': {
        'draw': True, # False to preserve empty containers in the IR
        'cmd': 'str', 
        'opts': {'key': 'value'}, 
        'path': 'str', 
        # to allow syntax such as `if node['tikz']['content']:` (tri-state)
        'content': {
          'txt': 'str', 
          # not sure img info is relevant...
          # 'img': {'path': 'str', 'embedded': False}
        }, 
        'extra': ['str', 'str'], # extra tikz command such as debug points
        'transforms': {} # svg transforms to be applied to a dedicated surrounding scope
      },
    'svg': {'tag': 'str', 'attrib': {'key': 'value'}}
  },
  {}, # ad noseam ...
  ]

def processOpts(opts):
  res = []
  for opt in opts:
    res.append("{}={}".format(opt, opts[opt]))
  return ','.join(res)


def emitTikz(ir):
  res = []
  for node in ir:
    tikz = node['tikz']
    if tikz['draw']:
      content = ''
      if 'content' in tikz and tikz['content']:
        content = '{' + tikz['content']['value'] + '}'
      
      specs=""
      if 'cell' in node:
        tikz['opts']['name'] = node['cell']['name']
        if node['cell']['overlays'] != "":
          tikz['opts']['visible on'] = node['cell']['overlays']

      if 'transforms' in tikz and tikz['transforms']:
        #FIXME: rotate does not apply to scope: 
        # https://tex.stackexchange.com/questions/310398/rotating-scope-in-tikz
        # should instead be applied to the node directly => no need for additional scope
        # res.append("\\begin{{scope}}[{}]".format(processOpts(tikz['transforms'])))
        for k in tikz['transforms']:
          if (k == 'rotate' and tikz['cmd'] == "node") or (k == 'rotate around' and tikz['cmd'] != 'node'):
            tikz['opts'][k] = tikz['transforms'][k]

      opts = processOpts(tikz['opts'])
      main = "\\{}[{}] {} {};".format(tikz['cmd'], opts, tikz['path'], content)
      
      
      res.append(main)
      if 'extra' in tikz and tikz['extra']:
        res += tikz['extra']

      # if 'transforms' in tikz and tikz['transforms']:
      #   res.append("\\end{scope}")

  return "\n".join(res)