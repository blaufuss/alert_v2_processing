#! /usr/bin/env python
from icecube import icetray, dataclasses, dataio, filterscripts
from icecube.realtime_gfu.muon_alerts import gfu_alert_eval
from icecube.filterscripts import filter_globals
from icecube.filterscripts.gfufilter import GammaFollowUp


import I3Tray
import glob
import json
import time
import sys

print ('start',time.asctime())
indir = sys.argv[1]
outdir = sys.argv[2]
outdir = sys.argv[2]
print ("indir:",indir)
print ("outdir:",outdir)
insearch = indir + '/*_*/Level2_IC86.*_Subrun0*_00000???.i3.zst'
#insearch = indir + '/Run00??????/Level2pass2_IC86.*_Subrun0*_00000???.i3.zst'
infiles = glob.glob(insearch)

day = indir[-4:]
outfile = outdir + '/Alerts_v2_' + day + '.i3'
#outfile = outdir + '/Alerts_v2_' + 'test' + '.i3'
print ('out: ', outfile)
infiles.sort()
print (infiles)

tray = I3Tray.I3Tray()

tray.AddModule("I3Reader", "reader", filenameList=infiles)

def find_v2_alerts(frame):
        keeper = False
        if frame.Has('FilterMask'):
                fm_gfu = frame['FilterMask']['GFUFilter_17']
                if fm_gfu.condition_passed:
                        #print(frame)
                        if frame.Has('GFU_valuesdict') and frame.Has('OnlineL2_SplineMPE'):
                                ev_json = json.loads(frame['GFU_valuesdict'].value)
                                #print(ev_json)
                                is_alert = gfu_alert_eval(ev_json, frame['OnlineL2_SplineMPE'])
                                if is_alert['pass_loose'] or is_alert['pass_tight']:
                                        ## found a gold or bronze
                                        print("********************Found Gold or Bronze")
                                        save_json = dataclasses.I3String(json.dumps(is_alert))
                                        frame['Alert_JSON'] = save_json
                                        keeper = True
                        else:
                                header = frame['I3EventHeader']
                                print("Missing JSON or Track for GFU eval:",header.run_id,header.event_id)
                fm_hese = frame['FilterMask']['HESEFilter_15']
                if fm_hese.condition_passed:
                        if frame.Has('HESE_CausalQTot'):
                                cqtot = frame['HESE_CausalQTot'].value
                                if cqtot > 6000.0: ## Std full HESE
                                        print("******************Found 6000pe HESE")
                                        #print('HESE:',frame)
                                        keeper = True
                        else:
                                print("Missing HESE_CausalQTot for HESE event !!!!")
        else:
                print('**************Missing FilterMask')
        return keeper

tray.AddModule(find_v2_alerts,'find_alerts',Streams=[icetray.I3Frame.Physics])

tray.AddModule("I3Writer","wrat",DropOrphanStreams=[icetray.I3Frame.DAQ],
               Streams=[icetray.I3Frame.DAQ, icetray.I3Frame.Physics],
               filename = outfile)

tray.Execute()
tray.Finish()
print ('end',time.asctime())
