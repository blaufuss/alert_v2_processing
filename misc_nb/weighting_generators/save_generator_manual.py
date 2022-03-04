#!/usr/bin/env python
from __future__ import print_function
import sys, pickle, os
from argparse import ArgumentParser

from icecube import weighting, icetray
from icecube.icetray import I3Units
from icecube.weighting.weighting import from_simprod, NeutrinoGenerator

usage = "usage: %prog [options]"
parser = ArgumentParser(usage)

parser.add_argument("-r", "--run", default=None, required=True, type=int,
                    help = "Run number you'd like to create a generator for. Will try to "
                    " load from simprod first and use that if it exists")
parser.add_argument("--nevents", default=None, type=int,
                    help = "Number of events produced from Neutrino-Generator. "
                    "Required if the dataset is not available in the simprod database.")
parser.add_argument("--emin", default=100, type=float,
                    help = "Minimum energy from generation in GeV")
parser.add_argument("--emax", default=1e8, type=float,
                    help = "Maximum energy from generation in GeV")
parser.add_argument("--gamma", default = None, type=float,
                    help = "Spectral index of the simulation from Neutrino-Generator. "
                    "Required if the dataset is not available in the simprod database.")
parser.add_argument("--flavor", default="NuMu", type=str,
                    help = "Particle type of simulation. Choose from NuE, NuMu, or NuTau.")
parser.add_argument("--zenmin", default=0, type=float,
                    help = "Minimum zenith from generation in degrees")
parser.add_argument("--zenmax", default=180, type=float,
                    help = "Maximum zenith from generation in degrees")
parser.add_argument("--injection_radius", default=950, type=float,
                    help = "Injection cylinder radius in meters")
parser.add_argument("--injection_height", default=1900, type=float,
                    help = "Injection cylinder height in meters")
parser.add_argument("--injection_mode", default='Cylinder',
                    help = "Nugen-style mode for injection of events. Set to Circle "
                    "for old NuGen sets that aligned the generation cylinder "
                    "with the particle direction or Cylinder for newer NuGen "
                    "that uses an upright cylinder")

options = parser.parse_args()

# Try just loading the generator from simprod, which is the 
# method least likely to cause problems
dataset = options.run
output_name = str(dataset)+".pckl"
worked = False
try:
    x = from_simprod(dataset)
    print("Dataset %i available in simprod database. Grabbing generator from that info." % dataset)
    pickle.dump(x, open(output_name, 'w'))
    worked = True
except:
    pass

if worked: 
    sys.exit(0)

print("Dataset " + str(dataset) +" was not available in simprod database. "
      " Building from scratch using parser arguments")
print(options)

if not (options.nevents > 0):
    print("ERROR: Cannot build generator without nevents information."
          " set that from the parser and verify other information is"
          " correct for your dataset")
    sys.exit(1)
if not (options.gamma):
    print("ERROR: Cannot build generator without gamma information."
          " set that from the parser and verify other information is"
          " correct for your dataset")
    sys.exit(1)


nugen_kwargs = dict()
if options.injection_mode == "Circle":
    nugen_kwargs['InjectionRadius'] = options.injection_radius
else:
    nugen_kwargs['CylinderHeight'] = options.injection_height
    nugen_kwargs['CylinderRadius'] = options.injection_radius
    
nugen_kwargs['InjectionMode'] = options.injection_mode

generator = NeutrinoGenerator(NEvents = options.nevents,
                              FromEnergy     = options.emin,
                              ToEnergy       = options.emax,
                              GammaIndex     = options.gamma,
                              NeutrinoFlavor = options.flavor,
                              ZenithMin      = options.zenmin * I3Units.deg,
                              ZenithMax      = options.zenmax * I3Units.deg,
                              **nugen_kwargs)

pickle.dump(generator, open(output_name, 'w'))
