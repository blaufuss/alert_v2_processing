#!/usr/bin/env python
import numpy as np

import glob

infiles = glob.glob("npy/*.npy")
infiles.sort()

print("In:", infiles)

all_arrays = []

for infile in infiles:
	all_arrays.append(np.load(infile))

np.save('all_mc_combined.npy',np.concatenate(all_arrays))
print('Wrote all_mc_combined.py')
