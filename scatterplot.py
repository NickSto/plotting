#!/usr/bin/env python
import sys
import argparse
import matplotliblib
import munger

OPT_DEFAULTS = {'xfield':1, 'yfield':2, 'xlabel':'X Value',
  'ylabel':'Y Value', 'color':'cornflowerblue'}
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


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)

if __name__ == "__main__":
  main()
