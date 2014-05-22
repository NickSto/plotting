#!/usr/bin/env python
import sys
import argparse
import collections
import munger
# also imports numpy, if certain summary methods are selected

DESCRIPTION = """Take a set of labeled values in a text file and group them by
the labels. By default, it will print the sum of the values for each label."""
EPILOG = """Caution: It holds the entire dataset in memory."""
USAGE = """cat file.txt | %(prog)s [options]
       %(prog)s [options] file.txt"""
OPT_DEFAULTS = {'label_field':1, 'data_field':2, 'method':'total'}

def main(argv):

  parser = argparse.ArgumentParser(
    usage=USAGE, description=DESCRIPTION, epilog=EPILOG
  )
  parser.set_defaults(**OPT_DEFAULTS)
  parser.add_argument('file', nargs='?', metavar='file.tsv',
    help='Data file. If omitted, data will be read from stdin. Each line '
      'should contain a label in one column and a number in another column.')
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
  parser.add_argument('-m', '--summary-method', dest='method',
    choices=('total', 'count', 'max', 'min', 'average', 'median', 'tsv', 'csv'),
    help='A method of summarizing the list of numbers under each label. Notes: '
      '"count" is just the number of occurrences of the label. "csv" just '
      'joins all the values with commas and prints that, effectively just '
      'collating them by label. "tsv" does the same, but with tabs. "average" '
      'and "median" require numpy.'
      'Default: %(default)s.')
  parser.add_argument('-M', '--summary-method-eval', dest='method_eval',
    help='Literal code for the summary method. This will be eval\'d and used '
      'as the function. Example: "lambda x: sum(map(abs, x))", '
      '"lambda x: \',\'.join(sorted(map(str, x)))"')
  parser.add_argument('-o', '--out-file', metavar='OUTPUT_FILE',
    help='Save the plot to this file instead of displaying it. The image '
      'format will be inferred from the file extension.')

  args = parser.parse_args(argv[1:])

  if args.file:
    input_stream = open(args.file, 'rU')
  else:
    input_stream = sys.stdin

  # Read data into dict, mapping values in the label column to values in the
  # data column (if they can be parsed to ints or floats).
  data = collections.OrderedDict()
  line_num = 0
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
      sys.stderr.write('Warning: Non-number encountered on line %d:\n%s\n' %
        (line_num, line.rstrip('\r\n')))
      continue
    values = data.get(label, [])
    values.append(value)
    data[label] = values

  if args.method_eval:
    try:
      summary_fxn = eval(args.method_eval)
    except Exception:
      sys.stderr.write('Error: Given eval code led to a parsing error. '
        'Full traceback below:\n\n')
      raise
  elif args.method == 'total':
    summary_fxn = sum
  elif args.method == 'count':
    summary_fxn = len
  elif args.method == 'max':
    summary_fxn = max
  elif args.method == 'min':
    summary_fxn = min
  elif args.method == 'csv':
    summary_fxn = lambda x: ','.join(map(str, x))
  elif args.method == 'tsv':
    summary_fxn = lambda x: '\t'.join(map(str, x))
  elif args.method == 'average':
    import numpy
    summary_fxn = numpy.mean
  elif args.method == 'median':
    import numpy
    summary_fxn = numpy.median

  summaries = collections.OrderedDict()
  for (label, values) in data.items():
    try:
      summaries[label] = summary_fxn(values)
    except Exception:
      if args.method_eval:
        sys.stderr.write('Error: Given eval code led to a runtime error. '
          'Full traceback below:\n\n')
      raise

  if args.out_file:
    output_stream = open(args.out_file, 'w')
  else:
    output_stream = sys.stdout

  for (label, summary) in summaries.items():
    output_stream.write("{}\t{}\n".format(label, summary))

  output_stream.close()


def fail(message):
  sys.stderr.write(message+"\n")
  sys.exit(1)

if __name__ == '__main__':
  main(sys.argv)