#!/bin/sh
cd ~/ml
source env3/bin/activate
cd pyprojects
cd stockScheduler
python stockScheduler.py $1
deactivate
