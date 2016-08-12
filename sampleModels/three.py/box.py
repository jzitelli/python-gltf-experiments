import json

import numpy as np

from three import *

scene = Scene()

output = '%s.json' % __file__[:-3]
with open(output, 'w') as f:
    f.write(json.dumps(scene.export(), indent=2, sort_keys=True))
    print('wrote "%s"' % output)
