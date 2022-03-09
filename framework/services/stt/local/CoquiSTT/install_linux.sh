#!/usr/bin/env bash
set -e
python3 -m venv venv_coqui
source venv_coqui/bin/activate
pip3 install --upgrade pip
pip3 install --upgrade wheel setuptools
pip3 install numpy
pip3 install quart
pip install stt
pip install numpy

