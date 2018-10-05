#!/bin/bash

cd ~/

mkdir -p ~/DRC

rm -f ~/master.zip*

wget https://github.com/Rsantct/DRC/archive/master.zip
unzip -o master.zip
rm -f ~/master.zip*

rm -rf ~/DRC
mv ~/DRC-master ~/DRC

chmod +x ~/DRC/drc_linpha/*.py
chmod +x ~/DRC/drc_linpha/*.sh
chmod +x ~/DRC/logsweep2TF/*.py
chmod +x ~/DRC/logsweep2TF/*.sh

rm ./update.sh  > /dev/null 2>&1

