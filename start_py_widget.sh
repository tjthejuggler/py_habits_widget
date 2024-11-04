#!/bin/bash
# wait 5 seconds
source /home/twain/miniconda3/etc/profile.d/conda.sh  # Replace with the path to your conda.sh
conda activate base
cd /home/twain/Projects/py_habits_widget
python /home/twain/Projects/py_habits_widget/py_widget.py # > ~/startup_log.txt 2>&1
 #terminal command to make this executable: chmod +x start_py_widget.sh
