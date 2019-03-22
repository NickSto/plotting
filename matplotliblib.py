#!/usr/bin/env python3
import argparse
import logging
import os
import sys
import matplotlib

# Prevent script from failing on headless machines with no X session:
# https://stackoverflow.com/questions/4706451/how-to-save-a-figure-remotely-with-pylab/4706614#4706614
if not os.getenv('DISPLAY'):
  matplotlib.use('Agg')

import matplotlib.pyplot

DEFAULTS = {'figsize':(8,6), 'dpi':80, 'width':640, 'height':480}


class PlotHelper(object):

  def __init__(self):
    self.figure = None
    self.axes = None
    self.dpi = None
    self.figsize = None

  def _get_or_add_argument_group(self, parser, group_name, group_title, existing_groups):
    if group_name in existing_groups:
      group = existing_groups[group_name]
    else:
      group = parser.add_argument_group(group_title)
      existing_groups[group_name] = group
    return group

  def add_arguments(self, parser, groups=None):
    """Add global matplotlib plotting arguments to the argparse parser."""
    if groups is None:
      groups = {}
    labels = self._get_or_add_argument_group(parser, 'labels', 'Labeling', groups)
    labels.add_argument('-T', '--title',
      help='Plot title. Default: None.')
    labels.add_argument('-X', '--x-label',
      help='Label for the X axis. Default: "%(default)s".')
    labels.add_argument('-Y', '--y-label',
      help='Label for the Y axis. Default: "%(default)s".')
    ranges = self._get_or_add_argument_group(parser, 'ranges', 'Ranges', groups)
    ranges.add_argument('-r', '--range', type=float, nargs=2, metavar='BOUND',
      help='Range of the axes. Both X and Y will have the same range. Give the '
        'lower bound, then the upper.')
    ranges.add_argument('--x-range', type=float, nargs=2, metavar='BOUND',
      help='Range of the X axis. Give the lower bound, then the upper.')
    ranges.add_argument('--y-range', type=float, nargs=2, metavar='BOUND',
      help='Range of the Y axis. Give the lower bound, then the upper.')
    data_disp = self._get_or_add_argument_group(parser, 'data_disp', 'Data appearance', groups)
    data_disp.add_argument('-C', '--color', default='cornflowerblue',
      help='Color for the plot data elements. Can use any CSS color. Default: '
        '"%(default)s".')
    image = self._get_or_add_argument_group(parser, 'image', 'Image output', groups)
    image.add_argument('-W', '--width', type=int,
      help='Width of the output image, in pixels. Default: {width}px.'.format(
        **DEFAULTS))
    image.add_argument('-H', '--height', type=int,
      help='Height of the output image, in pixels. Default: {height}px.'.format(
        **DEFAULTS))
    image.add_argument('-D', '--dpi', type=int,
      help='DPI of the image. If a height or width is given, a larger DPI will '
        'effectively just scale up the plot features, and a smaller DPI will '
        'scale them down. Default: {dpi}dpi.'.format(**DEFAULTS))
    image.add_argument('-o', '--out-file', metavar='OUTPUT_FILE',
      help='Save the plot to this file instead of displaying it. The image '
        'format will be inferred from the file extension.')
    log = self._get_or_add_argument_group(parser, 'log', 'Logging', groups)
    log.add_argument('-L', '--log', type=argparse.FileType('w'), default=sys.stderr,
      help='Print log messages to this file instead of to stderr. Warning: Will overwrite the file.')
    volume = log.add_mutually_exclusive_group()
    volume.add_argument('-q', '--quiet', dest='volume', action='store_const', const=logging.CRITICAL,
      default=logging.WARNING)
    volume.add_argument('-v', '--verbose', dest='volume', action='store_const', const=logging.INFO)
    volume.add_argument('--debug', dest='volume', action='store_const', const=logging.DEBUG)
    misc = self._get_or_add_argument_group(parser, 'misc', 'Misc', groups)
    misc.add_argument('--no-tight', action='store_true',
      help='Turn off tight_layout() (in case it\'s causing problems).')
    try:
      misc.add_argument('-h', '--help', action='help',
        help='Print this help text.')
    except argparse.ArgumentError as error:
      sys.stderr.write('Error: Problem adding --help argument. Make sure the ArgumentParser was '
                       'constructed with the add_help option set to False.\n\n')
      raise
    return parser

  def scale(self, defaults=DEFAULTS, **args):
    """Calculate the correct dpi and figsize to scale the image as the user
    requested.
    Required keyword arguments: 'dpi', 'width', 'height'
    """
    # assumptions
    assert 'dpi' in args and 'width' in args and 'height' in args, (
      'Necessary command-line arguments are missing.'
    )
    default_ratio = defaults['figsize'][0] / defaults['figsize'][1]
    pixel_ratio = defaults['width'] / defaults['height']
    assert default_ratio == pixel_ratio, 'Default aspect ratios do not match.'
    # If only a width or height is given, infer the other dimension, assuming the
    # default aspect ratio.
    if args['width'] and not args['height']:
      args['height'] = args['width'] / default_ratio
    elif args['height'] and not args['width']:
      args['width'] = args['height'] * default_ratio
    # Did the user specify a dpi?
    if args['dpi']:
      # If user gave a dpi, use it.
      # If user gives no width or height, a custom dpi will resize the plot.
      self.dpi = args['dpi']
      if args['width'] and args['height']:
        # If they did give a width/height, a custom dpi will scale the elements
        # in the plot.
        self.figsize = (args['width']/self.dpi, args['height']/self.dpi)
      else:
        self.figsize = defaults['figsize']
    elif args['width'] and args['height']:
      # If user gives a width or height and no dpi, scale both dpi and figsize.
      ratio = args['width'] / args['height']
      if ratio > default_ratio:
        scale = args['height'] / defaults['height']
        self.figsize = (
          defaults['figsize'][0] * (ratio/default_ratio),
          defaults['figsize'][1]
        )
      else:
        scale = args['width'] / defaults['width']
        self.figsize = (
          defaults['figsize'][0],
          defaults['figsize'][1] / (ratio/default_ratio)
        )
      self.dpi = scale * defaults['dpi']
    else:
      self.dpi = defaults['dpi']
      self.figsize = defaults['figsize']
    return self.dpi, self.figsize

  def set_ticks(self, tick_values, tick_labels, axis='x'):
    if axis.lower() == 'x':
      self.axes.set_xticks(tick_values)
      self.axes.set_xticklabels(tick_labels)
    elif axis.lower() == 'y':
      self.axes.set_yticks(tick_values, tick_labels)
      self.axes.set_yticklabels(tick_labels)

  def preplot(self, **args):
    """Set up the initial pyplot figure parameters, return an Axes object.
    Run this, get pyplot from it, and create your plot with it. E.g.:
      axes = matplotliblib.preplot(**vars(args))
      axes.hist(data)
    Required keyword arguments: 'dpi', 'width', 'height'
    """
    self.scale(**args)
    logging.debug("dpi: {}, figsize: {}".format(self.dpi, self.figsize))
    # Note: We can avoid pyplot with matplotlib.figure.Figure() instead, but then we need to configure
    # the backend manually. Example: https://matplotlib.org/gallery/api/agg_oo_sgskip.html
    self.figure = matplotlib.pyplot.figure(dpi=self.dpi, figsize=self.figsize)
    #TODO: Extra features:
    # figure.suptitle('Super title for entire plot', fontsize=22)
    # figure.set_figwidth(14)
    self.axes = self.figure.add_subplot(1, 1, 1)
    return self.axes

  def plot(self, **args):
    """Add options to a plot, and either display it or save it.
    Create your plot, then give the Axes object to this function, e.g.:
      axes.hist(data)
      matplotliblib.plot(axes, **vars(args))
    Required argparse arguments:
    'x_label', 'y_label', 'title', 'out_file'
    """
    required_opts = ('x_label', 'y_label', 'title', 'out_file')
    missing_opts = [opt for opt in required_opts if opt not in args]
    assert len(missing_opts) == 0, (
      'Necessary command-line arguments are missing: '+', '.join(missing_opts)
    )

    # Set X and Y ranges.
    if args.get('range') is not None:
      args['x_range'] = args['range']
      args['y_range'] = args['range']
    if args.get('x_range') is not None:
      self.axes.set_xlim(*args['x_range'])
    if args.get('y_range') is not None:
      self.axes.set_ylim(*args['y_range'])

    # Apply rest of settings
    self.axes.set_xlabel(args['x_label'])
    self.axes.set_ylabel(args['y_label'])
    if args['title']:
      self.axes.set_title(args['title'])
    if not args.get('no_tight'):
      matplotlib.pyplot.tight_layout()
    # Display or save
    if args['out_file']:
      matplotlib.pyplot.savefig(args['out_file'])
    else:
      matplotlib.pyplot.show()
    matplotlib.pyplot.close()
