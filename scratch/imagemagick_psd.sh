#!/bin/sh
#
# Create PSDs with ImageMagick
#

back="../../test/out/enhanced/2013-07-23_21-50-20_267353.png"
mask="../../test/out/segmented/2013-07-23_21-50-20_267353.png"

open $mask


convert mask.png back.png mask.png foo.psd
identify foo.psd
open -a /Applications/GIMP-2.10.app foo.psd

convert $mask -colorspace RGB -type truecolor -fuzz 0% -fill red -opaque black miff:- | convert miff:- -transparent white mask.png
identify foo.png
open mask.png

convert $back -colorspace RGB -type truecolor back.png
identify back.png
open back.png

convert back.png back.png mask.png foo.psd
identify foo.psd
open -a /Applications/GIMP-2.10.app foo.psd


convert foo.png -transparent white foo2.png
identify foo.png
open foo2.png

convert $mask -background white -alpha copy -type truecolormatte PNG32 foo.png
open foo.png

convert $mask -colorspace RGBA -type truecolor -transparent white -fuzz 0% -fill red -opaque black foo.png
open foo.png

convert $back $back foo.png foo.psd
open -a /Applications/GIMP-2.10.app foo.psd


convert \( -page +0+0 -label "label1" pic1.png -background none -mosaic -set colorspace RGB \) \( -page +0+0 -label "label2" pic2.png -background none -mosaic -set colorspace RGB \) \( -clone 0--1 -background none -mosaic \) -alpha Off -reverse output.psd


for f in $(ls -1 enhanced);
do
  echo $f
  convert segmented/$f enhanced/$f segmented/$f ${f%.*}.psd
done

exit 0
