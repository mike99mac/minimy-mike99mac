tar xzfv mimic3.tgz
cd mimic3
deactivate
make install
source .venv/bin/activate
pip install importlib-resources

# to run bin/mimic3 --model-dir voices/apope

