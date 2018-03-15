#!/usr/bin/env python
from __future__ import division
import sys
import time
import argparse
import matplotliblib
import munger

OPT_DEFAULTS = {'x_field':1, 'y_field':2, 'x_label':'X Value', 'time_unit':'sec',
                'y_label':'Y Value', 'unix_time':False, 'color':'cornflowerblue'}
USAGE = """cat file.txt | %(prog)s [options]
       %(prog)s [options] file.txt"""
DESCRIPTION = """Display a quick histogram of the input data, using matplotlib.
"""
EPILOG = """Caution: It holds the entire dataset in memory, as a list."""

def main():

  parser = argparse.ArgumentParser(usage=USAGE, description=DESCRIPTION,
    epilog=EPILOG)
  parser.set_defaults(**OPT_DEFAULTS)
  parser.add_argument('file', nargs='?', metavar='file.txt',
    help='Data file. If omitted, data will be read from stdin. Each line '
      'should contain two numbers.')
  parser.add_argument('-x', '--x-field', type=int,
    help='Use numbers from this input column as the x values. Give a 1-based '
      'index. Columns are whitespace-delimited unless --tab is given. '
      'Default column: %(default)s')
  parser.add_argument('-y', '--y-field', type=int,
    help='Use numbers from this input column as the y values. Give a 1-based '
      'index. Columns are whitespace-delimited unless --tab is given. '
      'Default column: %(default)s')
  parser.add_argument('-u', '--unix-time', choices=('X', 'Y', 'x', 'y'),
    help='Interpret the values for this axis as unix timestamps.')
  parser.add_argument('-U', '--time-unit', choices=('sec', 'second', 'seconds',
    'min', 'minute', 'minutes', 'hour', 'hours', 'hr', 'day', 'days', 'week',
    'weeks', 'month', 'months', 'year', 'years'),
    help='The unit with which to display the time field. Default: %(default)s')
  parser.add_argument('-f', '--field', type=int,
    help='1-dimensional data. Use this column as x values and set y as a '
      'constant (1).')
  parser.add_argument('-t', '--tab', action='store_true',
    help='Split fields on single tabs instead of whitespace.')

  matplotliblib.add_arguments(parser)
  args = parser.parse_args()

  if args.field and not args.y_range:
    args.y_range = (0, 2)

  if args.file:
    input_stream = open(args.file, 'rU')
  else:
    input_stream = sys.stdin

  if args.unix_time:
    now = int(time.time())
    time_conversion, time_label = get_time_conversion(args.time_unit)
    if args.x_label == OPT_DEFAULTS['x_label']:
      args.x_label = time_label
    time_field = args.unix_time.lower()

  # read data into list, parse types into ints or skipping if not possible
  x = []
  y = []
  line_num = 0
  for line in input_stream:
    line_num+=1
    if args.field:
      xval = munger.get_field(line, field=args.field, tab=args.tab, cast=True,
        errors='warn')
      yval = '1'
    else:
      (xval, yval) = munger.get_fields(line, fields=(args.x_field, args.y_field),
        tab=args.tab, cast=True, errors='warn')
    if xval is None or yval is None:
      continue
    if time_field == 'x':
      xval = (xval - now) / time_conversion
      # print xval
    elif time_field == 'y':
      yval = (yval - now) / time_conversion
    x.append(xval)
    y.append(yval)

  if input_stream is not sys.stdin:
    input_stream.close()

  assert len(x) == len(y), 'Length of x and y lists is different.'
  if len(x) == 0 or len(y) == 0:
    print 'No data found.'
    sys.exit(0)

  pyplot = matplotliblib.preplot(**vars(args))
  pyplot.scatter(x, y, c=args.color)
  matplotliblib.plot(pyplot, **vars(args))


def get_time_conversion(unit):
  if unit.startswith('sec'):
    return 1, 'Seconds ago'
  elif unit.startswith('min'):
    return 60, 'Minutes ago'
  elif unit.startswith('hour') or unit == 'hr':
    return 60*60, 'Hours ago'
  elif unit.startswith('day'):
    return 60*60*24, 'Days ago'
  elif unit.startswith('week'):
    return 60*60*24*7, 'Weeks ago'
  elif unit.startswith('month'):
    return 60*60*24*30.5, 'Months ago'
  elif unit.startswith('year'):
    return 60*60*24*365.25, 'Years ago'


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)


if __name__ == "__main__":
  main()
