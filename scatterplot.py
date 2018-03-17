#!/usr/bin/env python3
import sys
import time
import math
import logging
import argparse
import datetime
import matplotliblib
import munger
from utillib import datelib

MIN_TICKS = 4
OPT_DEFAULTS = {'x_label':'X Value', 'y_label':'Y Value'}
USAGE = """cat file.txt | %(prog)s [options]
       %(prog)s [options] file.txt"""
DESCRIPTION = """Display a quick scatterplot of the input data, using matplotlib."""
EPILOG = """Caution: It holds the entire dataset in memory, as a list."""


def make_parser():
  parser = argparse.ArgumentParser(usage=USAGE, description=DESCRIPTION,
    epilog=EPILOG)
  parser.set_defaults(**OPT_DEFAULTS)
  parser.add_argument('input', nargs='?', type=argparse.FileType('r'), default=sys.stdin,
    help='Data file. If omitted, data will be read from stdin. Each line '
      'should contain two numbers.')
  parser.add_argument('-x', '--x-field', type=int, default=1,
    help='Use numbers from this input column as the x values. Give a 1-based '
      'index. Columns are whitespace-delimited unless --tab is given. '
      'Default column: %(default)s')
  parser.add_argument('-y', '--y-field', type=int, default=2,
    help='Use numbers from this input column as the y values. Give a 1-based '
      'index. Columns are whitespace-delimited unless --tab is given. '
      'Default column: %(default)s')
  parser.add_argument('-f', '--field', type=int,
    help='1-dimensional data. Use this column as x values and set y as a '
      'constant (1).')
  parser.add_argument('-t', '--tab', action='store_true',
    help='Split fields on single tabs instead of whitespace.')
  timedate = parser.add_argument_group('Time/date handling')
  timedate.add_argument('-u', '--unix-time', choices=('X', 'Y', 'x', 'y'),
    help='Interpret the values for this axis as unix timestamps.')
  timedate.add_argument('--date', dest='time_disp', action='store_const', const='date', default='ago',
    help='Display the --unix-time field as the absolute date, not in units of how long ago.')
  timedate.add_argument('-U', '--time-unit', default='second', type=lambda s: datelib.UNIT_NAMES[s],
    choices=sorted(datelib.UNIT_NAMES.keys()),
    help='The unit with which to display the time field. Default: %(default)s')
  timedate.add_argument('--date-ticks', type=int, default=10,
    help='The maximum number of ticks to put on the time axis when using --date.')
  return parser


def main(argv):

  parser = make_parser()
  matplotliblib.add_arguments(parser)
  args = parser.parse_args(argv[1:])

  logging.basicConfig(stream=args.log, level=args.volume, format='%(message)s')

  if args.field and not args.y_range:
    args.y_range = (0, 2)

  if args.unix_time:
    if args.x_label == OPT_DEFAULTS['x_label']:
      if args.time_disp == 'ago':
        args.x_label = args.time_unit.name.capitalize() + 's ago'
      else:
        args.x_label = 'Date'
    time_field = args.unix_time.lower()
  else:
    time_field = None

  x, y = read_data(args.input, args.field, args.x_field, args.y_field, args.tab,
                   time_field, args.time_disp, args.time_unit)

  if args.input is not sys.stdin:
    args.input.close()

  assert len(x) == len(y), 'Length of x and y lists is different ({} != {}).'.format(len(x), len(y))
  if len(x) == 0 or len(y) == 0:
    logging.info('No data found.')
    sys.exit(0)

  make_plot(x, y, args, time_field)


def read_data(input, field, x_field, y_field, tab, time_field, time_disp, time_unit):
  # read data into lists, parse types into ints or skipping if not possible
  now = int(time.time())
  x = []
  y = []
  line_num = 0
  for line in input:
    line_num+=1
    if field:
      xval = munger.get_field(line, field=field, tab=tab, cast=True, errors='warn')
      yval = 1
    else:
      xval, yval = munger.get_fields(line, fields=(x_field, y_field),
                                     tab=tab, cast=True, errors='warn')
    if xval is None or yval is None:
      continue
    if time_disp == 'ago':
      if time_field == 'x':
        xval = (xval - now) / time_unit.seconds
      elif time_field == 'y':
        yval = (yval - now) / time_unit.seconds
    x.append(xval)
    y.append(yval)
  return x, y


def make_plot(x, y, args, time_field):
  axes = matplotliblib.preplot(**vars(args))
  axes.scatter(x, y, c=args.color)
  set_ticks(axes, x, y, args.unix_time, args.time_disp, time_field, args.date_ticks)
  matplotliblib.plot(axes, **vars(args))


def set_ticks(axes, x, y, unix_time, time_disp, time_field, date_ticks):
  if unix_time and time_disp == 'date':
    if time_field == 'x':
      time_max = max(x)
      time_min = min(x)
    elif time_field == 'y':
      time_max = max(y)
      time_min = min(y)
    max_ticks = date_ticks
    if max_ticks > MIN_TICKS:
      min_ticks = MIN_TICKS
    else:
      min_ticks = date_ticks - 1
    tick_values, tick_labels = get_time_ticks(time_min, time_max,
                                              min_ticks=min_ticks, max_ticks=max_ticks)
    if time_field == 'x':
      axes.set_xticks(tick_values)
      axes.set_xticklabels(tick_labels)
    elif time_field == 'y':
      axes.set_yticks(tick_values, tick_labels)
      axes.set_yticklabels(tick_labels)


def get_time_ticks(time_min, time_max, min_ticks=5, max_ticks=15):
  time_unit, multiple = get_tick_size(time_min, time_max, min_ticks, max_ticks)
  min_dt = datetime.datetime.fromtimestamp(time_min)
  dt = datelib.floor_datetime(min_dt, time_unit)
  first_tick_dt = datelib.increment_datetime(dt, time_unit)
  first_tick_value = int(first_tick_dt.timestamp())
  tick_values = []
  tick_labels = []
  tick_dt = first_tick_dt
  tick_value = first_tick_value
  while tick_value < time_max:
    #TODO: Abbreviate labels so that we don't keep repeating the same year/month/day/hour/etc.
    #      E.g. If the time period is a few hours, list "2015-05-10 20:00" for the first tick, then
    #      just "21:00" for the next one, and only show the date again when it changes
    #      ("2015-05-11 00:00").
    tick_values.append(tick_value)
    tick_label = tick_dt.strftime(time_unit.format_rounded.replace(' ', '\n'))
    tick_labels.append(tick_label)
    tick_dt = datelib.increase_datetime(tick_dt, time_unit, multiple)
    tick_value = int(tick_dt.timestamp())
  return tick_values, tick_labels


def get_tick_size(time_min, time_max, min_ticks, max_ticks):
  """Find a tick size for the time axis that gives between a min and max number of ticks.
  Determines what multiple of which TimeUnit and returns (time_unit, multiple)."""
  time_period = time_max - time_min
  min_multiple = sys.maxsize
  min_multiple_unit = None
  for time_unit in datelib.TIME_UNITS:
    ticks = time_period / time_unit.seconds
    if ticks < min_ticks:
      multiple = 1
    elif ticks > max_ticks:
      multiple = math.ceil(ticks/max_ticks)
    else:
      return time_unit, 1
    ticks = time_period / (time_unit.seconds*multiple)
    if min_ticks <= ticks <= max_ticks and multiple < min_multiple:
      min_multiple = multiple
      min_multiple_unit = time_unit
  return min_multiple_unit, min_multiple


def fail(message):
  logging.critical(message)
  sys.exit(1)


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except BrokenPipeError:
    pass
