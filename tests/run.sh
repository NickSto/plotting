#!/usr/bin/env bash
cd $(dirname $0)

# functional tests

echo -e "\thistoplot.py ::: histoplot.txt.in:"
../histoplot.py -H 240 -D 60 histoplot.txt.in -o histoplot-tmp.png
if [[ $(crc32 histoplot-tmp.png) == $(crc32 histoplot-H240-D60.png.out) ]]; then
  echo "Output is identical to histoplot-H240-D60.png.out"
else
  echo "Output does not match histoplot-H240-D60.png.out"
fi
rm histoplot-tmp.png

echo -e "\tscatterplot.py ::: data1.tsv.in:"
../scatterplot.py -x 3 data1.tsv.in -o scatterplot-tmp.png
if [[ $(crc32 scatterplot-tmp.png) == $(crc32 scatterplot1.png.out) ]]; then
  echo "Output is identical to scatterplot1.png.out"
else
  echo "Output does not match scatterplot1.png.out"
fi
rm scatterplot-tmp.png
