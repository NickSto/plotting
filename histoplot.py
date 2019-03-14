#!/usr/bin/env python3
import sys
import logging
import argparse
import matplotliblib
import munger

DEFAULT_BINS = 20
OPT_DEFAULTS = {'x_label':'Value', 'y_label':'Frequency'}
USAGE = """cat file.txt | %(prog)s [options]
       %(prog)s [options] file.txt"""
DESCRIPTION = """Display a quick histogram of the input data, using matplotlib.
"""
EPILOG = """Caution: It holds the entire dataset in memory, as a list."""


def make_parser():
  parser = argparse.ArgumentParser(usage=USAGE, description=DESCRIPTION,
    epilog=EPILOG)
  parser.set_defaults(**OPT_DEFAULTS)
  parser.add_argument('input', nargs='?', type=argparse.FileType('r'), default=sys.stdin,
    help='Data file. If omitted, data will be read from stdin. Each line '
      'should contain one number.')
  parser.add_argument('-f', '--field', type=int, default=1,
    help='Read this column from the input. Give a 1-based index. Columns are '
      'whitespace-delimited unless --tab is given. Default column: %(default)s.')
  parser.add_argument('-t', '--tab', action='store_true',
    help='Split fields on single tabs instead of whitespace.')
  parser.add_argument('-u', '--unity', action='store_true',
    help='Use a bin size of 1.')
  parser.add_argument('-b', '--bins', type=int,
    help='Number of histogram bins. Default: {}.'.format(DEFAULT_BINS))
  parser.add_argument('-B', '--bin-edges', nargs='+', type=float,
    help='Specify the exact edges of each bin. Give the value of each bin edge '
      'as a separate argument. Overrides --bins.')
  #TODO: clarify relationship between bin_range, x_range, and range
  parser.add_argument('-R', '--bin-range', type=float, nargs=2, metavar='BOUND',
    help='Range of the bins only. This will be used when calculating the size '
      'of the bins (unless -B is given), but it won\'t affect the scaling of '
      'the X axis. Give the lower bound, then the upper.')
  return parser


def main(argv):

  plotter = matplotliblib.PlotHelper()

  parser = make_parser()
  plotter.add_arguments(parser)
  args = parser.parse_args(argv[1:])

  logging.basicConfig(stream=args.log, level=args.volume, format='%(message)s')

  data, top, bottom = read_data(args.input, args.field, args.tab)

  if args.input is not sys.stdin:
    args.input.close()

  if len(data) == 0:
    logging.info('No data.')
    sys.exit(0)

  bins, bin_range = get_edges(args.bins, args.bin_edges, args.bin_range, args.range, args.unity,
                              top, bottom)

  make_plot(plotter, data, args, bins, bin_range)


def read_data(input, field, tab):
  # read data into list, parse types into ints or skipping if not possible
  data = []
  top = -sys.maxsize
  bottom = sys.maxsize
  line_num = 0
  for line in input:
    line_num+=1
    value = munger.get_field(line, field=field, tab=tab, cast=True, errors='warn')
    if value < bottom:
      bottom = value
    if value > top:
      top = value
    data.append(value)
  return data, top, bottom


def get_edges(bins_arg, bin_edges, bin_range_arg, range_arg, unity, top, bottom):
  # Compute plot settings from arguments
  if bin_edges:
    bins = bin_edges
  elif bins_arg:
    bins = bins_arg
  else:
    bins = DEFAULT_BINS
  if range_arg:
    bin_range = range_arg
  else:
    bin_range = bin_range_arg
  if unity:
    if bins_arg:
      if bin_range_arg:
        fail('Error: Cannot meet constraints of --bins {}, --bin-range {} {}, and --unity.'
             .format(bins_arg, bin_range_arg[0], bin_range_arg[1]))
      else:
        bin_range = (bottom-0.5, bottom+bins_arg+0.5)
        print('Saw --bins {}, using --bins {} --bin-range {} {}.'
              .format(bins_arg, bins, bin_range[0], bin_range[1]))
    else:
      if bin_range_arg:
        bins = bin_range_arg[1] - bin_range_arg[0] + 1
        bin_range = (bin_range_arg[0]-0.5, bin_range_arg[1]+0.5)
      else:
        bins = top - bottom + 1
        bin_range = (bottom-0.5, top+0.5)
        if bins > 200:
          fail('Error: Range of data is {}. Using that many bins will be hard to read. If you '
               'really want that many, please provide it explicitly to --bins.'.format(bins))
  return bins, bin_range


def make_plot(plotter, data, args, bins, bin_range):
  # make the actual plot
  axes = plotter.preplot(**vars(args))
  axes.hist(data, bins=bins, range=bin_range, color=args.color)
  plotter.plot(**vars(args))


def fail(message):
  logging.critical(message)
  sys.exit(1)


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except BrokenPipeError:
    pass
