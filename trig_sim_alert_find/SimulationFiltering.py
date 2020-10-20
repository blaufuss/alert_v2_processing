#!/usr/bin/env python
### The simulation L1 processing script ###

import os
import sys 
import time
import subprocess, logging

from I3Tray import *
from icecube import icetray, dataclasses, dataio, filter_tools, trigger_sim
from icecube import phys_services
from icecube.filterscripts import filter_globals
from icecube.filterscripts.all_filters import OnlineFilter
from icecube.phys_services.which_split import which_split
from math import log10, cos, radians
from optparse import OptionParser
from os.path import expandvars

def make_parser():
    """Make the argument parser"""
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("-i", "--input", action="store",
        type=str, default="", dest="infile",
        help="Input i3 file(s)  (use comma separated list for multiple files)")
    parser.add_argument("-g", "--gcd", action="store",
        type=str, default="", dest="gcdfile",
        help="GCD file for input i3 file")
    parser.add_argument("-o", "--output", action="store",
        type=str, default="", dest="outfile",
        help="Output i3 file")
    parser.add_argument("-n", "--num", action="store",
        type=int, default=-1, dest="num",
        help="Number of frames to process")
    parser.add_argument("--qify", action="store_true",
        default=False, dest="qify",
        help="Apply QConverter, use if file is P frame only")
    parser.add_argument("--MinBiasPrescale", action="store",
        type=int, default=None, dest="MinBiasPrescale",
        help="Set the Min Bias prescale to something other than default")
    parser.add_argument("--photonicsdir", action="store",
        type=str, default="/cvmfs/icecube.opensciencegrid.org/data/photon-tables",
        dest="photonicsdir", help="Directory with photonics tables")
    parser.add_argument("--enable-gfu", action="store_true",
        default=False, dest="GFU",
        help="Do not run GFU filter")
    parser.add_argument("--log-level",
        type=str, default="WARN", dest="LOG_LEVEL",
        help="Sets the logging level (ERROR, WARN, INFO, DEBUG, TRACE)")
    parser.add_argument("--log-filename",
        type=str, default=None, dest="logfn",
        help="If set logging is redirected to the specified file.")
    parser.add_argument("--needs_wavedeform_spe_corr", action="store_true",
        default=False, dest="needs_wavedeform_spe_corr",
        help="apply_spe_corection in wavedeform.")

    return parser


def main(options, stats={}):
    """The main L1 script"""
    tray = I3Tray()

    if not options['infile']:
        raise Exception('You need to specify an input file with the -i or --input parameter.')
    
    if not options['gcdfile']:
        raise Exception('You need to specify a GCD file with the -g or --gcd parameter.')

    if not options['outfile']:
        raise Exception('You need to specify an output file with the -o or --output parameter.')    

    log_levels = {"error" : icetray.I3LogLevel.LOG_ERROR,
                  "warn" : icetray.I3LogLevel.LOG_WARN,
                  "info" : icetray.I3LogLevel.LOG_INFO,
                  "debug" : icetray.I3LogLevel.LOG_DEBUG,
                  "trace" : icetray.I3LogLevel.LOG_TRACE}

    if options['LOG_LEVEL'].lower() in log_levels.keys():
        icetray.set_log_level(log_levels[options['LOG_LEVEL'].lower()])
    else:
        logging.warning("log level option %s not recognized.")
        logging.warning("Options are ERROR, WARN, INFO, DEBUG, and TRACE.")
        logging.warning("Sticking with default of WARN.")
        icetray.set_log_level(icetray.I3LogLevel.LOG_WARN)

    if options['logfn']:
        pid = os.getpid()
        icetray.logging.rotating_files("%s.%d" % (options['logfn'], pid))
        
    # make list of input files from GCD and infile
    if isinstance(options['infile'],list):
        infiles = [options['gcdfile']]
        infiles.extend(options['infile'])
    else:
        infiles = [options['gcdfile'], options['infile']]
    
    # test access to input and output files
    for f in infiles:
        if not os.access(f,os.R_OK):
            raise Exception('Cannot read from %s'%f)
    def test_write(f):
        if f:
            try:
                open(f,'w')
            except IOError:
                raise Exception('Cannot write to %s'%f)
            finally:
                os.remove(f)
    test_write(options['outfile'])

    ########################################

    tray = I3Tray()
    
    tray.Add(dataio.I3Reader, "reader", filenamelist=infiles)
    # shim the D frame with IceTop Bad Doms.  Add empty lists.
    def shim_bad_icetopdoms(frame):
        frame[filter_globals.IcetopBadTanks] = dataclasses.I3VectorTankKey()
        frame[filter_globals.IceTopBadDoms] = dataclasses.I3VectorOMKey()
    tray.AddModule(shim_bad_icetopdoms,'Base_shim_icetopbads',
                Streams = [icetray.I3Frame.DetectorStatus])
    
    # run online filters
    tray.AddSegment(OnlineFilter, "OnlineFilter", 
                    decode=False, simulation=True,
                    vemcal_enabled=False,
                    needs_wavedeform_spe_corr=False,
                    gfu_enabled=True,
                    alert_followup=True,
                    alert_followup_omit_GCD_diff=True,
                    )
    
    # make random service
    seed = os.getpid()
    filter_mask_randoms = phys_services.I3GSLRandomService(seed)

    # override MinBias Prescale
    filterconfigs = filter_globals.filter_pairs + filter_globals.sdst_pairs
    if options['MinBiasPrescale']:
        for i,filtertuple in enumerate(filterconfigs):
            if filtertuple[0] == filter_globals.FilterMinBias:
                del filterconfigs[i]
                filterconfigs.append((filtertuple[0],options['MinBiasPrescale']))
                break
    icetray.logging.log_info("%s" % str(filterconfigs))
    
    # Generate filter Masks for all P frames
    tray.AddModule(filter_tools.FilterMaskMaker, "MakeFilterMasks",
                   OutputMaskName = filter_globals.filter_mask,
                   FilterConfigs = filterconfigs,
                   RandomService = filter_mask_randoms)

    # Merge the FilterMasks
    tray.AddModule("OrPframeFilterMasks", "make_q_filtermask",
                   InputName = filter_globals.filter_mask,
                   OutputName = filter_globals.qfilter_mask)

    ## Check for interesting filters
    def filter_good(frame):
        keepme = False
        q_fm = frame['FilterMask']
        if q_fm['GFUFilter_17'].prescale_passed:
            #print('Found GFU!')
            keepme = True
        if q_fm['EHEAlertFilter_15'].prescale_passed:
            print('Found EHE alert!')
            keepme = True
        if q_fm['EHEFilter_13'].prescale_passed:
            #print('Found EHE!')
            keepme = True
        if q_fm['HESEFilter_15'].prescale_passed:
            print('Found HESE!')
            keepme = True
        if q_fm['GRECOOnlineFilter_19'].prescale_passed:
            #print('Found GrecoOnline!')
            keepme = True
        if q_fm['EstresAlertFilter_18'].prescale_passed:
            #print('Found ESTRES!')
            keepme = True
        return keepme

    # filter events that pass one of the alert selections....
    tray.AddModule(filter_good,'checkfm', Streams=[icetray.I3Frame.Physics])

    #Q+P frame specific keep module needs to go first, as KeepFromSubstram
    #will rename things, let's rename post keep.  
    def is_Q(frame):
        return frame.Stop==frame.DAQ

    simulation_keeps = [
            'BackgroundI3MCTree',
            'BackgroundI3MCTreePEcounts',
            'BackgroundI3MCPESeriesMap',
            'BackgroundI3MCTree_preMuonProp',
            'BackgroundI3MCTree_preMuonProp_RNGState',
            'BackgroundMMCTrackList',
            'BeaconLaunches',
            'CorsikaInteractionHeight',
            'CorsikaWeightMap',
            'EventProperties',
            'GenerationSpec',
            'I3LinearizedMCTree',
            'I3MCTree',
            'I3MCTreePEcounts',
            'I3MCTree_preMuonProp',
            'I3MCTree_preMuonProp_RNGState',
            'I3MCPESeriesMap',
            'I3MCPESeriesMapWithoutNoise',
            'I3MCPESeriesMapParticleIDMap',
            'I3MCPulseSeriesMap',
            'I3MCPulseSeriesMapParticleIDMap',
            'I3MCPulseSeriesMapPrimaryIDMap',
            'I3MCWeightDict',
            'LeptonInjectorProperties',
            'MCHitSeriesMap',
            'MCPrimary',
            'MCPrimaryInfo',
            'MMCTrackList',
            'PolyplopiaInfo',
            'PolyplopiaPrimary',
            'RNGState',
            'SignalI3MCPEs',
            'SimTrimmer', # for SimTrimmer flag
            'TimeShift', # the time shift amount
            'WIMP_params', # Wimp-sim
            'noise_weight', # weights for noise-only vuvuzela simulations
            'I3GENIEResultDict' # weight informaition for GENIE simulations
           ]

    keep_before_merge = filter_globals.q_frame_keeps + [
                            'InIceDSTPulses', # keep DST pulse masks
                            'IceTopDSTPulses',
                            'CalibratedWaveformRange', # keep calibration info
                            'UncleanedInIcePulsesTimeRange',
                            'SplitUncleanedInIcePulses',
                            'SplitUncleanedInIcePulsesTimeRange',
                            'SplitUncleanedInIceDSTPulsesTimeRange',
                            'CalibrationErrata',
                            'SaturationWindows',
                            'InIceRawData', # keep raw data for now
                            'IceTopRawData',
                           ] + simulation_keeps

    tray.AddModule("Keep", "keep_before_merge",
                   keys = keep_before_merge,
                   If=is_Q
                   )

    # ## second set of prekeeps, conditional on filter content, based on newly created Qfiltermask
    # #Determine if we should apply harsh keep for events that failed to pass any filter
    # ##  Note: excluding the sdst_streams entries

    # tray.AddModule("I3IcePickModule<FilterMaskFilter>","filterMaskCheckAll",
    #                FilterNameList = filter_globals.filter_streams,
    #                FilterResultName = filter_globals.qfilter_mask,
    #                DecisionName = "PassedAnyFilter",
    #                DiscardEvents = False, 
    #                Streams = [icetray.I3Frame.DAQ]
    #                )
    # def do_save_just_superdst(frame):
    #     if frame.Has("PassedAnyFilter"):
    #         if not frame["PassedAnyFilter"].value:
    #             return True    #  <- Event failed to pass any filter.  
    #         else:
    #             return False # <- Event passed some filter

    #     else:
    #         icetray.logging.log_error("Failed to find key frame Bool!!")
    #         return False

    # keep_only_superdsts = filter_globals.keep_nofilterpass+[
    #                          'PassedAnyFilter',
    #                          'InIceDSTPulses',
    #                          'IceTopDSTPulses',
    #                          'SplitUncleanedInIcePulses',
    #                          'SplitUncleanedInIcePulsesTimeRange',
    #                          'SplitUncleanedInIceDSTPulsesTimeRange',
    #                          'RNGState',
    #                          ] + simulation_keeps
    # tray.AddModule("Keep", "KeepOnlySuperDSTs",
    #                keys = keep_only_superdsts,
    #                If = do_save_just_superdst
    #                )
        
    # ## Now clean up the events that not even the SuperDST filters passed on.
    # tray.AddModule("I3IcePickModule<FilterMaskFilter>","filterMaskCheckSDST",
    #                FilterNameList = filter_globals.sdst_streams,
    #                FilterResultName = filter_globals.qfilter_mask,
    #                DecisionName = "PassedKeepSuperDSTOnly",
    #                DiscardEvents = False,
    #                Streams = [icetray.I3Frame.DAQ]
    #                )

    # def dont_save_superdst(frame):
    #     if frame.Has("PassedKeepSuperDSTOnly") and frame.Has("PassedAnyFilter"):
    #         if frame["PassedAnyFilter"].value:
    #             return False  #  <- these passed a regular filter, keeper
    #         elif not frame["PassedKeepSuperDSTOnly"].value:
    #             return True    #  <- Event failed to pass SDST filter.  
    #         else:
    #             return False # <- Event passed some  SDST filter
    #     else:
    #         icetray.logging.log_error("Failed to find key frame Bool!!")
    #         return False

    # tray.AddModule("Keep", "KeepOnlyDSTs",
    #                keys = filter_globals.keep_dst_only
    #                       + ["PassedAnyFilter","PassedKeepSuperDSTOnly",
    #                          filter_globals.eventheader],
    #                If = dont_save_superdst
    #                )


    # ## Frames should now contain only what is needed.  now flatten, write/send to server
    # ## Squish P frames back to single Q frame, one for each split:
    # tray.AddModule("KeepFromSubstream","null_stream",
    #                StreamName = filter_globals.NullSplitter,
    #                KeepKeys = filter_globals.null_split_keeps,
    #                )

    # in_ice_keeps = filter_globals.inice_split_keeps + filter_globals.onlinel2filter_keeps
    # in_ice_keeps = in_ice_keeps + ['I3EventHeader',
    #                                'SplitUncleanedInIcePulses',
    #                                'SplitUncleanedInIcePulsesTimeRange',
    #                                'TriggerSplitterLaunchWindow',
    #                                'I3TriggerHierarchy',
    #                                'GCFilter_GCFilterMJD']
    # tray.AddModule("Keep", "inice_keeps",
    #                keys = in_ice_keeps,
    #                If = which_split(split_name=filter_globals.InIceSplitter),
    #                )


    # tray.AddModule("KeepFromSubstream","icetop_split_stream",
    #                StreamName = filter_globals.IceTopSplitter,
    #                KeepKeys = filter_globals.icetop_split_keeps,
    #                )

    # # Apply small keep list (SuperDST/SmallTrig/DST/FilterMask for non-filter passers
    # # Remove I3DAQData object for events not passing one of the 'filters_keeping_allraw'
    # tray.AddModule("I3IcePickModule<FilterMaskFilter>","filterMaskCheck",
    #                FilterNameList = filter_globals.filters_keeping_allraw,
    #                FilterResultName = filter_globals.qfilter_mask,
    #                DecisionName = "PassedConventional",
    #                DiscardEvents = False,
    #                Streams = [icetray.I3Frame.DAQ]
    #                )

    # ## Clean out the Raw Data when not passing conventional filter
    # def I3RawDataCleaner(frame):
    #     if not (('PassedConventional' in frame and 
    #              frame['PassedConventional'].value == True) or 
    #             ('SimTrimmer' in frame and
    #              frame['SimTrimmer'].value == True)
    #            ):
    #         frame.Delete('InIceRawData')
    #         frame.Delete('IceTopRawData')

    # tray.AddModule(I3RawDataCleaner,"CleanErrataForConventional",
    #                Streams=[icetray.I3Frame.DAQ])

    ###################################################################
    ########### WRITE STUFF                  ##########################
    ###################################################################
    
    # Write the physics and DAQ frames
    tray.AddModule("I3Writer", "EventWriter",
                   filename=options['outfile'],
                   DropOrphanStreams=[icetray.I3Frame.DAQ],
                   Streams=[icetray.I3Frame.DAQ,icetray.I3Frame.Physics,
                            icetray.I3Frame.TrayInfo, icetray.I3Frame.Simulation,
                            icetray.I3Frame.Stream('M')] # added M-frame
                   )

    

    # make it go
    if options['num'] >= 0:
        tray.Execute(options['num'])
    else:
        tray.Execute()

    

    # print more CPU usage info. than speicifed by default
    #tray.PrintUsage(fraction=1.0) 
    #for entry in tray.Usage():
    #    stats[entry.key()] = entry.data().usertime
    
    # clean up forcefully in case we're running this in a loop
    del tray


if __name__ == '__main__':
    # run as script from the command line
    # get parsed args
    parser = make_parser()
    args = parser.parse_args()

    # convert to dictionary
    opts = vars(args)
    opts['infile'] = opts['infile'].split(',')

    # call main function
    main(opts)

