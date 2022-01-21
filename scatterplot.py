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
  parser = argparse.ArgumentParser(usage=USAGE, description=DESCRIPTION, epilog=EPILOG,
    add_help=False)
  parser.set_defaults(**OPT_DEFAULTS)
  groups = {}
  input = parser.add_argument_group('Input data')
  groups['input'] = input
  input.add_argument('input', nargs='?', type=argparse.FileType('r'), default=sys.stdin,
    help='Data file. If omitted, data will be read from stdin. Each line '
      'should contain two numbers.')
  input.add_argument('-x', '--x-field', type=int, default=1,
    help='Use numbers from this input column as the x values. Give a 1-based '
      'index. Columns are whitespace-delimited unless --tab is given. '
      'Default column: %(default)s')
  input.add_argument('-y', '--y-field', type=int, default=2,
    help='Use numbers from this input column as the y values. Give a 1-based '
      'index. Columns are whitespace-delimited unless --tab is given. '
      'Default column: %(default)s')
  input.add_argument('-f', '--field', type=int,
    help='1-dimensional data. Use this column as x values and set y as a '
         'constant (1).')
  input.add_argument('-t', '--tab', action='store_true',
    help='Split fields on single tabs instead of whitespace.')
  input.add_argument('--head', type=int,
    help='Only plot the first X data points in the input file.')
  input.add_argument('--tail', type=int,
    help='Only plot the last X data points in the input file.')
  data_disp = parser.add_argument_group('Data appearance')
  groups['data_disp'] = data_disp
  data_disp.add_argument('-S', '--point-size', type=int, default=30,
    help='Size of the data points in the plot. Default: %(default)s')
  data_disp.add_argument('-B', '--bar', action='store_true',
    help='Display with bars instead of points. Does not work with --tag-field.')
  heat = parser.add_argument_group('Heatmap')
  groups['heat'] = heat
  heat.add_argument('-M', '--heatmap', action='store_true',
    help='Make a heatmap: essentially a 2D histogram of how many points are in each rectangle. '
         'Not compatible with multiple data series.')
  heat.add_argument('-b', '--bins', type=int, default=10,
    help='Use this number of 1-dimensional bins on each axis, so that the actual number of 2-'
      'dimensional bins is the square of this. Default: %(default)s')
  heat.add_argument('--x-bins', type=int,
    help='Divide the X axis into this many bins. Overrides --bins.')
  heat.add_argument('--y-bins', type=int,
    help='Divide the Y axis into this many bins. Overrides --bins.')
  heat.add_argument('--color-bar', metavar='Title',
    help='Provide a legend labeling the heatmap colors, and use this title.')
  heat.add_argument('--log-scale', action='store_true',
    help='Plot the log10 of the counts, not the absolute counts.')
  heat.add_argument('--log0', action='store_true',
    help='Adjust the counts to make zeroes plottable: log10(counts + 0.1) + 1')
  heat.add_argument('--color-map', default='viridis',
    help='Color scheme to use for the heatmap. "Blues" is a nice one where 0 is white. Or, for a '
      'more classic "heat" scale, "jet". Default: %(default)s')
  multi = parser.add_argument_group('Multiple data series')
  groups['multi'] = multi
  multi.add_argument('-g', '--tag-field', type=int,
    help='The input contains multiple data series, distinguished by this column. '
         'This column should identify which series the data point belongs to. It can be any '
         'string, as long as it uniquely identifies the series. '
         'This option will produce a single plot, with each series as its own line.')
  multi.add_argument('-l', '--label-field', type=int,
    help='When doing a multiplot using --tag-field, use this field for the name to use in the '
         'legend. This is useful when the unique identifier isn\'t a human-readable name.')
  multi.add_argument('-c', '--changing-only', action='store_true',
    help='When plotting multiple data series (with --tag-field), omit any series where the '
         'Y values don\'t change.')
  multi.add_argument('-n', '--normalize', action='store_true',
    help='When plotting multiple data series (with --tag-field), normalize each series so that '
         'the maximum is 1 (or the minimum is -1, if its absolute value is greater).')
  multi.add_argument('--line', action='store_true',
    help='Do a line plot instead of a scatter plot.')
  timedate = parser.add_argument_group('Time/date handling')
  groups['timedate'] = timedate
  timedate.add_argument('-u', '--unix-time', choices=('X', 'Y', 'x', 'y'),
    help='Interpret the values for this axis as unix timestamps.')
  timedate.add_argument('--date', dest='time_disp', action='store_const', const='date', default='ago',
    help='Display the --unix-time field as the absolute date, not in units of how long ago.')
  timedate.add_argument('-U', '--time-unit', default='second', type=lambda s: datelib.UNIT_NAMES[s],
    choices=datelib.TIME_UNITS,
    help='The unit with which to display the time field. Choose one of: {}. Default: %(default)s'
         .format(', '.join(sorted(datelib.UNIT_NAMES.keys()))))
  timedate.add_argument('--date-ticks', type=int, default=8,
    help='The maximum number of ticks to put on the time axis when using --date.')
  timedate.add_argument('-s', '--start',
    help='Only plot points at or after this time. Give a unix timestamp or a quantity like "10s", '
         '"25 minutes", "10yr", etc., to specify an amount of time in the past.')
  timedate.add_argument('-e', '--end',
    help='Only plot points at or before this time. Same format as --start.')
  return parser, groups


def main(argv):

  plotter = matplotliblib.PlotHelper()

  parser, groups = make_parser()
  plotter.add_arguments(parser, groups)
  args = parser.parse_args(argv[1:])

  logging.basicConfig(stream=args.log, level=args.volume, format='%(message)s')

  if args.tag_field is not None and args.tail is not None:
    fail('Error: --tail is not yet supported at the same time as --tag-field.')

  if args.field and not args.y_range:
    args.y_range = (0, 2)
  if (args.start or args.end) and not args.unix_time:
    fail('Error: --start and --end are invalid without --unix-time.')

  if args.heatmap and args.tag_field:
    fail('Error: --heatmap not compatible with --tag-field.')

  start = get_start_or_end(args.start)
  end = get_start_or_end(args.end)

  # Figure out some time parameters.
  if args.unix_time:
    if args.x_label == OPT_DEFAULTS['x_label']:
      if args.time_disp == 'ago':
        args.x_label = args.time_unit.name.capitalize() + 's ago'
      else:
        args.x_label = 'Date'
    time_field = args.unix_time.lower()
  else:
    time_field = None

  # Read the data in.
  fields = {'1':args.field, 'x':args.x_field, 'y':args.y_field, 'tag':args.tag_field,
            'label':args.label_field, 'time':time_field}
  x, y, labels = read_data(args.input, fields, args.tab, args.time_disp, args.time_unit, args.head,
                           start, end)
  if args.input is not sys.stdin:
    args.input.close()

  if args.tail is not None:
    x = x[-args.tail:]
    y = y[-args.tail:]

  # Postprocess some of the data for multiplots.
  if args.tag_field:
    if args.changing_only:
      trim_static_series(x, y)
    if args.normalize:
      normalize(x, y)

  # Do some checking of the data.
  if args.tag_field:
    empty = True
    for tag in x:
      if len(x[tag]) != len(y[tag]):
        fail('Length of x and y lists for series {!r} is different ({} != {}).'
             .format(tag, len(x[tag]), len(y[tag])))
      if len(x[tag]) > 0:
        empty = False
  else:
    assert len(x) == len(y), 'Length of x and y lists is different ({} != {}).'.format(len(x), len(y))
    empty = len(x) == 0
  if empty:
    logging.info('No data found.')
    return 0

  # Bin the data for heatmaps.
  if args.heatmap:
    xbins = ybins = args.bins
    if args.x_bins:
      xbins = args.x_bins
    if args.y_bins:
      ybins = args.y_bins
    heatmap, extents = get_heatmap_counts(x, y, xbins, ybins)
    logging.debug('extents: xmin: {0}, xmax: {1}, ymin: {2}, ymax: {3}'.format(*extents))
    if args.log_scale:
      log_transform_heatmap(heatmap, args.log0)

  # Create the Axes object.
  axes = plotter.preplot(**vars(args))

  # Plot the data.
  if args.heatmap:
    # aspect='auto' to prevent it from forcing the x and y axis scales to be equal.
    image = axes.imshow(heatmap, cmap=args.color_map, extent=extents, aspect='auto', origin='lower',
                        interpolation='nearest')
    if args.color_bar is not None:
      colorbar = plotter.figure.colorbar(image)
      if args.color_bar:
        colorbar.set_label(args.color_bar)
  elif args.tag_field is None:
    if args.bar:
      axes.bar(x, y, color=args.color)
    else:
      axes.scatter(x, y, c=args.color, s=args.point_size)
  else:
    handles = []
    tags = list(x.keys())
    for tag in tags:
      x_series = x[tag]
      y_series = y[tag]
      if args.line:
        retval = axes.plot(x_series, y_series)
        handles.append(retval[0])
      else:
        retval = axes.scatter(x_series, y_series, s=args.point_size)
        handles.append(retval)
    if args.label_field:
      labels_list = [labels[tag] for tag in tags]
    else:
      labels_list = tags
    axes.legend(handles=handles, labels=labels_list)

  # Label time axis.
  if args.unix_time and args.time_disp == 'date':
    multiplot = args.tag_field is not None
    set_time_ticks(plotter, x, y, multiplot, args.unix_time, args.time_disp, time_field, args.date_ticks)

  # Do final adjustments and show the plot.
  plotter.plot(**vars(args))


def read_data(input, fields, tab, time_disp, time_unit, head, start, end):
  # read data into lists, parse types into ints or skipping if not possible
  if fields['1'] is None:
    field_columns = (fields['x'], fields['y'], fields['tag'], fields['label'])
    casts = (True, True, False, False)
  labels = {}
  now = int(time.time())
  #TODO: Get and return the xmaxes and ymaxes while reading the input.
  x_serieses = {}
  y_serieses = {}
  x = []
  y = []
  line_num = 0
  for line in input:
    line_num+=1
    if fields['1'] is not None:
      xval = munger.get_field(line, field=fields['1'], tab=tab, cast=True, errors='warn')
      yval = 1
    else:
      xval, yval, tag, label = munger.get_fields(line, fields=field_columns, tab=tab, casts=casts,
                                          errors='warn')
    if xval is None or yval is None:
      continue
    if head is not None and line_num > head:
      break
    # Timestamp stuff.
    if fields['time']:
      if fields['time'] == 'x':
        timestamp = xval
      elif fields['time'] == 'y':
        timestamp = yval
      if start is not None and timestamp < start:
        continue
      elif end is not None and timestamp > end:
        continue
      if time_disp == 'ago':
        if fields['time'] == 'x':
          xval = (xval - now) / time_unit.seconds
        elif fields['time'] == 'y':
          yval = (yval - now) / time_unit.seconds
    if fields['tag'] is None:
      x.append(xval)
      y.append(yval)
    else:
      # Multiple data series stuff.
      if tag not in x_serieses:
        x_serieses[tag] = []
        y_serieses[tag] = []
        labels[tag] = label
      x_serieses[tag].append(xval)
      y_serieses[tag].append(yval)
  if fields['tag'] is None:
    return x, y, None
  else:
    return x_serieses, y_serieses, labels


def trim_static_series(x_serieses, y_serieses):
  tags = list(y_serieses.keys())
  for tag in tags:
    changed = False
    y_series = y_serieses[tag]
    first = y_series[0]
    for val in y_series:
      if val != first:
        changed = True
        break
    if not changed:
      logging.info('No variation in series {!r}. Skipping..'.format(tag))
      del x_serieses[tag]
      del y_serieses[tag]


def normalize(x_serieses, y_serieses):
  y_serieses_new = {}
  for tag, y_series in y_serieses.items():
    ymax = max(y_series)
    ymin = min(y_series)
    # Divide all values by the one furthest from 0.
    factor = max(ymax, abs(ymin))
    if factor == 0:
      # If all the values are 0, just leave them as 0's.
      factor = 1
    for i, yval in enumerate(y_series):
      y_series[i] = yval/factor


def get_heatmap_counts(x, y, xbins, ybins):
  # Initialize the heatmap counts.
  heatmap = []
  for ybin in range(ybins):
    heatmap.append([0] * xbins)
  # Get the min/max data values.
  xmin = min(x)
  xmax = max(x)
  ymin = min(y)
  ymax = max(y)
  # Make the first bin centered on the minimum value and the last bin centered on the maximum one.
  xbin_width = (xmax - xmin) / (xbins-1)
  xleft_edge = xmin - xbin_width/2
  ybin_height = (ymax - ymin) / (ybins-1)
  ybottom_edge = ymin - ybin_height/2
  for xval, yval in zip(x, y):
    # bins are half-open: [bin_min, bin_max).
    xbin = int((xval - xleft_edge) / xbin_width)
    ybin = int((yval - ybottom_edge) / ybin_height)
    heatmap[ybin][xbin] += 1
  return heatmap, (xmin, xmax, ymin, ymax)


def format_heatmap_counts_debug(heatmap):
  """Create an ascii matrix of heatmap counts.
  Returns a series of lines (no newlines), ready to be printed."""
  out_lines = []
  max_val = max([max(row) for row in heatmap])
  fwidth = int(math.log10(max_val)+1)
  fmt_str = '{:'+str(fwidth)+'d}'
  for row in reversed(heatmap):
    for i in range(len(row)):
      out_lines.append(' '.join([fmt_str.format(val) for val in row]))
  return out_lines


def log_transform_heatmap(heatmap, zero_offset=False):
  for row in heatmap:
    for i in range(len(row)):
      if zero_offset:
        row[i] = math.log10(row[i]+0.1)+1
      else:
        row[i] = math.log10(row[i])


def set_time_ticks(plotter, x, y, multiplot, unix_time, time_disp, time_field, date_ticks):
  params = get_tick_params(x, y, multiplot, unix_time, time_disp, time_field, date_ticks)
  tick_values, tick_labels = get_time_ticks(*params)
  plotter.set_ticks(tick_values, tick_labels, axis=time_field)


def get_start_or_end(time_str):
  try:
    return int(time_str)
  except TypeError:
    return None
  except ValueError:
    pass
  now = int(time.time())
  seconds_ago = datelib.time_str_to_seconds(time_str)
  return now - seconds_ago


def get_tick_params(x, y, multiplot, unix_time, time_disp, time_field, date_ticks):
  if time_field == 'x':
    time_min, time_max = get_min_max(x, multiplot)
  elif time_field == 'y':
    time_min, time_max = get_min_max(y, multiplot)
  max_ticks = date_ticks
  if max_ticks > MIN_TICKS:
    min_ticks = MIN_TICKS
  else:
    min_ticks = date_ticks - 1
  return time_min, time_max, min_ticks, max_ticks


def get_min_max(data, multiplot):
  min_val = None
  max_val = None
  if multiplot:
    for series in data.values():
      series_min = min(series)
      series_max = max(series)
      if min_val is None:
        min_val = series_min
        max_val = series_max
      else:
        min_val = min(min_val, series_min)
        max_val = max(max_val, series_max)
  else:
    min_val = min(data)
    max_val = max(data)
  return min_val, max_val


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
