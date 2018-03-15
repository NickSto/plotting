#!/usr/bin/env python3
from __future__ import division
import sys
import time
import argparse
import datetime
import matplotliblib
import munger

OPT_DEFAULTS = {'x_field':1, 'y_field':2, 'x_label':'X Value', 'time_unit':'sec', 'time_disp':'ago',
                'y_label':'Y Value', 'date_ticks':10, 'unix_time':False, 'color':'cornflowerblue'}
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
  parser.add_argument('-u', '--unix-time', choices=('X', 'Y', 'x', 'y'),
    help='Interpret the values for this axis as unix timestamps.')
  parser.add_argument('--date', dest='time_disp', action='store_const', const='date',
    help='Display the --unix-time field as the absolute date, not in units of how long ago.')
  parser.add_argument('-U', '--time-unit', choices=('sec', 'second', 'seconds',
    'min', 'minute', 'minutes', 'hour', 'hours', 'hr', 'day', 'days', 'week',
    'weeks', 'month', 'months', 'year', 'years'),
    help='The unit with which to display the time field. Default: %(default)s')
  parser.add_argument('--date-ticks', type=int,
    help='The maximum number of ticks to put on the time axis when using --date.')

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
    time_unit = get_time_unit(args.time_unit)
    if args.x_label == OPT_DEFAULTS['x_label']:
      if args.time_disp == 'ago':
        args.x_label = time_unit.name.capitalize() + 's ago'
      else:
        args.x_label = 'Date'
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
    if args.time_disp == 'ago':
      if time_field == 'x':
        xval = (xval - now) / time_unit.seconds
      else:
        yval = (yval - now) / time_unit.seconds
    x.append(xval)
    y.append(yval)

  if input_stream is not sys.stdin:
    input_stream.close()

  assert len(x) == len(y), 'Length of x and y lists is different.'
  if len(x) == 0 or len(y) == 0:
    sys.stderr.write('No data found.\n')
    sys.exit(0)

  pyplot = matplotliblib.preplot(**vars(args))
  pyplot.scatter(x, y, c=args.color)

  if args.unix_time and args.time_disp == 'date':
    if time_field == 'x':
      time_max = max(x)
      time_min = min(x)
    elif time_field == 'y':
      time_max = max(y)
      time_min = min(y)
    tick_values, tick_labels = get_time_ticks(time_min, time_max, num_ticks=args.date_ticks)
    if time_field == 'x':
      pyplot.xticks(tick_values, tick_labels)
    elif time_field == 'y':
      pyplot.yticks(tick_values, tick_labels)

  matplotliblib.plot(pyplot, **vars(args))


def get_time_unit(unit):
  for time_unit in TIME_UNITS:
    if unit == time_unit.name or unit == time_unit.abbrev:
      return time_unit


def get_time_ticks(time_min, time_max, num_ticks=15):
  time_unit = get_tick_size(time_min, time_max, num_ticks)
  # Python 2:
  # min_dt = datetime.datetime.utcfromtimestamp(time_min)
  min_dt = datetime.datetime.fromtimestamp(time_min)
  dt = floor_datetime(min_dt, time_unit)
  first_tick_dt = increment_datetime(dt, time_unit)
  first_tick_value = int(first_tick_dt.timestamp())
  # Python 2:
  # epoch_start = datetime.datetime.utcfromtimestamp(0)
  # first_tick_value = int((first_tick_dt - epoch_start).total_seconds())
  tick_values = []
  tick_labels = []
  tick_dt = first_tick_dt
  tick_value = first_tick_value
  while tick_value < time_max:
    tick_values.append(tick_value)
    tick_label = tick_dt.strftime(time_unit.format_rounded)
    tick_labels.append(tick_label)
    tick_dt = increment_datetime(tick_dt, time_unit)
    tick_value = int(tick_dt.timestamp())
  # If there are too many ticks, eliminate some.
  # This can happen if the time span is larger than num_ticks years.
  if len(tick_values) > num_ticks:
    keep_frequency = int((len(tick_values)-1) / num_ticks) + 1
    new_tick_values = []
    new_tick_labels = []
    i = 0
    for tick_value, tick_label in zip(tick_values, tick_labels):
      if i % keep_frequency == 0:
        new_tick_values.append(tick_value)
        new_tick_labels.append(tick_label)
      i += 1
    tick_values = new_tick_values
    tick_labels = new_tick_labels
  return tick_values, tick_labels


def get_tick_size(time_min, time_max, num_ticks=15):
  time_period = time_max - time_min
  for time_unit in TIME_UNITS:
    if time_period/time_unit.seconds <= num_ticks:
      return time_unit
  return Year


def floor_datetime(dt, time_unit):
  """Round a datetime down to the nearest time_unit.
  dt must be a datetime.datetime and time_unit must be a TimeUnit."""
  dt_dict = {}
  for this_unit in TIME_UNITS:
    if this_unit == Week:
      continue
    unit_value = getattr(dt, this_unit.name)
    if time_unit == Week and this_unit == Day:
      unit_value = unit_value - (unit_value % 7)
    elif this_unit.seconds < time_unit.seconds:
      unit_value = this_unit.min_value
    dt_dict[this_unit.name] = unit_value
  return datetime.datetime(**dt_dict)


def increment_datetime(dt, time_unit):
  dt_dict = {}
  carry = 0
  for this_unit in TIME_UNITS:
    if this_unit == Week:
      if time_unit == Week:
        unit_value = dt.day + 7
        this_unit = Day
      else:
        continue
    else:
      unit_value = getattr(dt, this_unit.name)
      if this_unit == time_unit:
        unit_value += 1
      unit_value += carry
    # Figure out whether the unit overflowed and needs to be wrapped to zero, with a carry.
    if this_unit == Day:
      if dt.month == 2:
        if is_leap_year(dt.year):
          max_value = 29
        else:
          max_value = 28
      else:
        max_value = MONTH_LENGTHS[dt.month]
    else:
      max_value = this_unit.max_value
    if unit_value > max_value:
      carry = 1
      unit_value = this_unit.min_value + unit_value - max_value - 1
    else:
      carry = 0
    dt_dict[this_unit.name] = unit_value
  return datetime.datetime(**dt_dict)


def is_leap_year(year):
  return (year % 4 == 0 and year % 100 != 0) or year % 400 == 0


class TimeUnit(object):
  pass

class Second(TimeUnit):
  name = 'second'
  abbrev = 'sec'
  format = '%S'
  format_rounded = '%Y-%m-%d %H:%M:%S'
  min_value = 0
  max_value = 59
  seconds = 1

class Minute(TimeUnit):
  name = 'minute'
  abbrev = 'min'
  format = '%M'
  format_rounded = '%Y-%m-%d %H:%M'
  min_value = 0
  max_value = 59
  seconds = Second.seconds * 60

class Hour(TimeUnit):
  name = 'hour'
  abbrev = 'hr'
  format = '%H'
  format_rounded = '%Y-%m-%d %H:00'
  min_value = 0
  max_value = 23
  seconds = Minute.seconds * 60

class Day(TimeUnit):
  name = 'day'
  abbrev = 'day'
  format = '%d'
  format_rounded = '%Y-%m-%d'
  min_value = 1
  max_value = 31
  seconds = Hour.seconds * 24

class Week(TimeUnit):
  name = 'week'
  abbrev = 'week'
  format = '%d'
  format_rounded = '%Y-%m-%d'
  min_value = 0
  max_value = 4
  seconds = Day.seconds * 7

class Month(TimeUnit):
  name = 'month'
  abbrev = 'mo'
  format = '%b'
  format_rounded = '%b %Y'
  min_value = 1
  max_value = 12
  seconds = int(Day.seconds * 30.5)

class Year(TimeUnit):
  name = 'year'
  abbrev = 'yr'
  format = '%Y'
  format_rounded = '%Y'
  min_value = -sys.maxsize
  max_value = sys.maxsize
  seconds = int(Day.seconds * 365.25)

TIME_UNITS = (Second, Minute, Hour, Day, Week, Month, Year)

MONTH_LENGTHS = {1:31, 2:28, 3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30, 10:31, 11:30, 12:31}


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)


if __name__ == "__main__":
  main()
