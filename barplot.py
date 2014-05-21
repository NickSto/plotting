#!/usr/bin/env python
# a stacked bar plot with errorbars
import numpy as np
import matplotlib.pyplot as plt
import matplotliblib
import collections

OPT_DEFAULTS = {'label_field':1, 'data_field':2, 'bins':10}
USAGE = """cat file.txt | %(prog)s [options]
       %(prog)s [options] file.txt"""
DESCRIPTION = """Display a quick bar plot of the input data, using matplotlib.
"""
EPILOG = """Caution: It holds the entire dataset in memory."""

def main(argv):

  parser = argparse.ArgumentParser(usage=USAGE, description=DESCRIPTION,
    epilog=EPILOG)
  parser.set_defaults(**OPT_DEFAULTS)
  parser.add_argument('file', nargs='?', metavar='file.txt',
    help='Data file. If omitted, data will be read from stdin. Each line '
      'should contain one number.')
  parser.add_argument('-l', '--label-field', type=int,
    help='Read this column from the input as the data labels. Give a 1-based '
    'index. Columns are whitespace-delimited unless --tab is given. Default '
    'column: %(default)s.')
  parser.add_argument('-f', '--data-field', type=int,
    help='Read this column from the input as the data. Give a 1-based index. '
    'Columns are whitespace-delimited unless --tab is given. Default column: '
    '%(default)s.')
  parser.add_argument('-t', '--tab', action='store_true',
    help='Split fields on single tabs instead of whitespace.')
  parser.add_argument('-o', '--out-file', metavar='OUTPUT_FILE',
    help='Save the plot to this file instead of displaying it. The image '
      'format will be inferred from the file extension.')
  parser.add_argument('-r', '--range', type=float, nargs=2, metavar='BOUND',
    help='Range of the Y axis. Give the lower bound, then the upper.')

  matplotliblib.add_arguments(parser)
  args = parser.parse_args(argv)

  if args.file:
    input_stream = open(args.file, 'rU')
  else:
    input_stream = sys.stdin

  # Read data into dict, mapping values in the label column to values in the
  # data column (if they can be parsed to ints or floats).
  data = collections.OrderedDict()
  line_num = 0
  integers = True
  for line in input_stream:
    line_num+=1
    (label, value_str) = munger.get_fields(
      line,
      fields=(args.label_field, args.data_field),
      tab=args.tab,
      errors='warn'
    )
    if label is None or value_str is None:
      continue
    try:
      value = to_num(value_str)
    except ValueError:
      sys.stderr.write('Warning: Non-number encountered on line %d: %s\n' %
        (line_num, line.rstrip('\r\n')))
      continue
    values = data.get(label, [])
    values.append(value)
    data[label] = values

  


def to_num(num_str):
  try:
    return int(num_str)
  except ValueError:
    return float(num_str)

N = 5
menMeans   = (20, 35, 30, 35, 27)
womenMeans = (25, 32, 34, 20, 25)
menStd     = (2, 3, 4, 1, 2)
womenStd   = (3, 5, 2, 3, 3)
ind = np.arange(N)    # the x locations for the groups
width = 0.35       # the width of the bars: can also be len(x) sequence

p1 = plt.bar(ind, menMeans,   width, color='r', yerr=womenStd)
p2 = plt.bar(ind, womenMeans, width, color='y',
             bottom=menMeans, yerr=menStd)

plt.ylabel('Scores')
plt.title('Scores by group and gender')
plt.xticks(ind+width/2., ('G1', 'G2', 'G3', 'G4', 'G5') )
plt.yticks(np.arange(0,81,10))
plt.legend( (p1[0], p2[0]), ('Men', 'Women') )

plt.show()
