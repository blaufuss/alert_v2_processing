#!/bin/sh

###########################################################
# This is a bash script that write a dag, which defines 
# your jobs with a submit file, and any arguments (i.e.
# your python script, I/O files, and/or any arguments that
# you would have passed when running your python scripts
# locally). Note that this file simplies 'write', you don't
# have to use bash at all; python works as well. (I just 
# wanted to force myself to learn another language)
# 
# To run this script:
# $ ./builddag.sh > my_dag.dag
#
# Regardless of how you generate the output, the dag, 
# my_dag.dag, is the dagman file that you will submit. 
# Each job in this my_dag.dag is defined by the keyword
# "JOB" followed by an unique job id and the submit file:
#
# JOB job_id submit.sub
#
# Often, your python scripts take arguments. To change
# the arguments for each of jobs, you can use the "VARS"
# keyword:
#
# VARS $job_id job_name=\"$job_name\" infile=\"$infile\"
#
# NOTE:: MAKE SURE NONE OF THE PATHS HERE POINTS TO I3HOME
#        EITHER /data/condor_build/ OR /data/i3store0/ OR
#        /data/i3scratch0/
#
# After you have the dag file (my_dag.dag), you can submit
# your jobs via:
#
# $ condor_submit_dag -config dagman.config my_dag.dag
#
# dagmain.config is where you can set the max jobs per 
# time, number of jobs per interval, etc.
############################################################

##################################################################
#### recall my command line:
#### python dumb_core.py --outfile <string> -nsteps <int>
####                     --coeff <float> --sleep <float> --verbose
##################################################################

jobbase='alertv2_20_'
script="/data/user/blaufuss/alert_find/find_alerts.py"
outdir="/data/user/blaufuss/historical_alerts/2020"
counter=100
### seq <min> <stepsize> <max>
#for a in `seq 0.1 0.01 1.0`; do
for infile in `ls -d /data/exp/IceCube/2020/filtered/level2/[0-1]*`; do
    let counter=counter+1
    command="python ${script} ${infile} ${outdir}"
    jobname=$jobbase$counter
    JOBID=$jobbase$counter
    echo JOB $JOBID /data/user/blaufuss/alert_finder/submit.sub
    echo VARS $JOBID JOBNAME=\"$jobname\" command=\"$command\"
done

