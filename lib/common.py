# custom format for nice number display, see below, neither .2f nor .3g are corresponding to the need 
# https://stackoverflow.com/questions/2389846/python-decimals-format
def f(x):
    return ('%.2f' % x).rstrip('0').rstrip('.')

def getNiceNumber(string):
  try:
    return int(string) # avoid ugly .0 everywhere in the result
  except:
    return float(string) # might still raise an exception but would be for good reasons: unparsable number
