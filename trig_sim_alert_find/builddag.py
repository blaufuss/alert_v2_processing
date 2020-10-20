#!/usr/bin/env python

#Let's make a dag.
# ./build_dag.py > newdag.dag
# then hand it to condor
import numpy as np
import os
import glob

jobbase = 'alertv2_sim'
script="/data/user/blaufuss/alert_find_sim/SimulationFiltering.py"
outdir="/data/user/blaufuss/alert_find_sim/20878_alerts/"
#gcd="/data/user/blaufuss/alert_find_sim/GeoCalibDetectorStatus_IC86.All_Pass2.i3.gz"
gcd="/data/sim/IceCube/2016/filtered/level2/neutrino-generator/20878/0000000-0000999/GeoCalibDetectorStatus_IC86.All_Pass2.i3.gz"

infile_list = glob.glob('/data/sim/IceCube/2016/generated/neutrino-generator/20878/0001000-0001999/IC86.*.i3.zst')
infile_list.sort()

counter = 1000

for infile in infile_list:
        outfile = outdir + 'Alertv2_'+ os.path.split(infile)[1]
        command = f'python {script} -g {gcd} -i {infile} -o {outfile}'
        job_id = f'{jobbase}_{counter}'
        print(f'JOB {job_id} /data/user/blaufuss/alert_find_sim/submit.sub')
        print(f'VARS {job_id} JOBNAME="{job_id}" command="{command}"')
        counter += 1
