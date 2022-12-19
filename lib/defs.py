from .config import App

#################################
# TIKZ STANDALONE SETUP
#################################

PREAMBLE="""
\\documentclass{standalone}
\\usepackage{tikz}
\\usepackage[sc]{mathpazo}
\\begin{document}
"""

# NB: CODE TO SCALE EFFICIENTLY a tikzpicture:
# % COPY-PASTING from stack-overflow, I have no idea how the following jacobian transforms works ...
# % https://tex.stackexchange.com/questions/515300/can-i-scale-all-line-widths-in-a-tikzpicture

# % Jacobians have already been used in https://tex.stackexchange.com/q/86897/138900
# % https://tex.stackexchange.com/a/496418 and https://tex.stackexchange.com/a/506249/194703
# \makeatletter
# \tikzset{scale line widths/.style={%
# /utils/exec=\pgfgettransformentries{\tmpa}{\tmpb}{\tmpc}{\tmpd}{\tmp}{\tmp}%
# \pgfmathsetmacro{\myJacobian}{sqrt(abs(\tmpa*\tmpd-\tmpb*\tmpc))}%
# \pgfmathsetlength\pgflinewidth{\myJacobian*0.4pt}%
# \def\tikz@semiaddlinewidth##1{\pgfmathsetmacro{\my@lw}{\myJacobian*##1}%
# \tikz@addoption{\pgfsetlinewidth{\my@lw pt}}\pgfmathsetlength\pgflinewidth{\my@lw pt}},%
# thin}}
# \makeatother

# \begin{tikzpicture}[x=1pt,y=1pt,scale=0.3, every node/.style={scale=0.3}, scale line widths]

# tikzset styles to be defined here with color definitions
def SCALE():
  return """
%% Edit this value to scale the entire picture, including position, nodes and details 
\\def\\scale{{{}}}
""".format(App.config()['TEX_SCALE_FACTOR'])


def BASE():
  opts = ["x=1pt,y=1pt,scale=\\scale, every node/.style={scale=\\scale}"]

  conf = App.config()
  if 'ADDITIONAL_TIKZPICTURE_OPTIONS' in conf:
    opts += conf['ADDITIONAL_TIKZPICTURE_OPTIONS']
  opts = ",".join(opts)

  tikzset = []
  if 'ADDITIONAL_TIKZSET' in conf:
    tikzset.append("\\tikzset{%")
    tikzset += conf['ADDITIONAL_TIKZSET']
    tikzset.append("}%")
  tikzset = "\n".join(tikzset)


  return """
{}
\\newdimen\\basept
\\basept=1pt
\\newdimen\\pt
\\pt=\\scale\\basept
\\begin{{tikzpicture}}[{}]
  """.format(tikzset, opts)

def TIKZ_START(): 
  return BASE() if App.config()['NO_SCALE_DEF'] else SCALE() + BASE()


TIKZ_END="""
\\end{tikzpicture}
"""

FOOTER="""
\\end{document}
"""
