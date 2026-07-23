with open('/media/sandesh/extra-ssd/dataset/dataset-make/drishti_pipeline/config.py', 'r') as f:
    code = f.read()
code = code.replace(',,', ',')
with open('/media/sandesh/extra-ssd/dataset/dataset-make/drishti_pipeline/config.py', 'w') as f:
    f.write(code)
