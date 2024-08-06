# SPDX-License-Identifier: MIT
"""spm_mkconf.py

Create spm_config.h from bin and txt definition.
"""

import sys

model = b'SPM24121'

if len(sys.argv) != 4:
    print('Usage: spm_mkconf.py spm_config.bin spm_config.txt spm_config.h')
    sys.exit(1)

src = None
with open(sys.argv[1], 'rb') as f:
    src = f.read()

cfg = {}
with open(sys.argv[2]) as f:
    for l in f:
        v = l.split(maxsplit=2)
        if len(v) == 3 and v[0].startswith('0x'):
            oft = int(v[0], 16)
            mask = int(v[1], 16)
            if oft not in cfg:
                cfg[oft] = 0
            cfg[oft] |= mask

model_bytes = []
cfg_bytes = []
cfg_vals = []
for k in sorted(cfg):
    cfg_bytes.append('0x%02x' % k)
    cfg_vals.append('0x%02x' % src[k])
for c in model:
    model_bytes.append('0x%02x' % c)

with open(sys.argv[3], 'w') as f:
    f.write('\n\n#include <stdint.h>\n\n#define SPM_CFGLEN\t0x%02x\n' %
            len(cfg_vals))
    f.write('#define SPM_MODEL\t {')
    f.write(', '.join(model_bytes))
    f.write(' }\n')
    f.write('static const uint8_t cfg_bytes[SPM_CFGLEN] = {\n')
    f.write(', '.join(cfg_bytes))
    f.write('\n};\nstatic const uint8_t cfg_vals[SPM_CFGLEN] = {\n')
    f.write(', '.join(cfg_vals))
    f.write('\n};\n')
