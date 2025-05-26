#!/bin/bash
cd /home/twain/Projects/py_habits_widget
export QT_QPA_PLATFORM=xcb
export QT_X11_NO_MITSHM=1
python3 py_widget.py