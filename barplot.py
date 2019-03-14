#!/usr/bin/env python3
# a stacked bar plot with errorbars
from __future__ import division
import sys
import numpy
import argparse
import collections
import matplotliblib
import munger

OPT_DEFAULTS = {'label_field':1, 'data_field':2, 'bar_width':0.75}
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
  parser.add_argument('-w', '--bar-width', type=float,
    help='Relative width of each bar. A relative width of 1 means each bar '
    'wil be the full width of its interval, with no spacing between bars. '
    'Default: %(default)s.')

  plotter = matplotliblib.PlotHelper()

  plotter.add_arguments(parser)
  args = parser.parse_args(argv[1:])

  if args.file:
    input_stream = open(args.file, 'rU')
  else:
    input_stream = sys.stdin

  labels = []
  values = []
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
      value = munger.to_num(value_str)
    except ValueError:
      sys.stderr.write('Warning: Non-number encountered on line %d: %s\n' %
        (line_num, line.rstrip('\r\n')))
      continue
    labels.append(label)
    values.append(value)

  xlocations = numpy.arange(len(labels))
  width = args.bar_width * len(labels) / 5

  # make the actual plot
  axes = plotter.preplot(**vars(args))
  axes.bar(xlocations, values, width, color=args.color)
  plotter.set_ticks(xlocations + width/2, labels, axis='x')
  plotter.plot(**vars(args))


if __name__ == '__main__':
  main(sys.argv)
