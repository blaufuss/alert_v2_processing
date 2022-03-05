#!/usr/bin/env python

import sys
import numpy as np
import json
import glob


from icecube.hdfwriter import I3HDFWriter
from icecube import icetray, dataclasses, dataio
from icecube.realtime_gfu.muon_alerts import gfu_alert_eval
from icecube.realtime_hese.HESE_alerts_v2 import hese_alert_eval
from icecube.realtime_ehe.EHE_alerts_v2 import ehe_alert_eval
from I3Tray import *

tray = I3Tray()

outfile_ext = sys.argv[1]
infiles = glob.glob(sys.argv[2])

infiles.sort()
outfile = os.path.join(os.getenv('TMPDIR'),outfile_ext)


print('Outfile:',outfile)
print('Infile:',infiles)

tray.AddModule("I3Reader", "reader", filenameList=infiles)

def pass_alerts_check(frame):
    pass_gfu = False
    pass_hesev2_gold = False
    pass_hesev2_bronze = False
    pass_ehev2_gold = False
    pass_gfu_gold = False
    pass_gfu_bronze = False
    #pframe = afile.pop_physics()
    if frame.Has('AlertNamesPassed'):
        alert_list = frame['AlertNamesPassed']
        if len(alert_list) == 0:
            #print("what no alert??")
            return False
        if frame.Has('AlertShortFollowupMsg'):
            ev_json = json.loads(frame['AlertShortFollowupMsg'].value)
            ## Pad the json to be like "I3Live"
            message = {'value': { 'data' : ev_json}}
        else:
            if len(alert_list) > 0:
                ## Complain only if there should be a message from any alert
                print('Missing event dict!')
        if 'neutrino' in alert_list:
            pass_gfu = True
            is_alert = gfu_alert_eval(message)
            #if we got an alert, let's disect it
            if is_alert['pass_loose'] or is_alert['pass_tight']:
                if is_alert['pass_tight']:
                    pass_gfu_gold = True
                if is_alert['pass_loose']:
                    pass_gfu_bronze = True
                ## found a gold or bronze
                #print("********************Found Gold or Bronze")
                #print("GFU:",is_alert)
                #print('GFU')
        if 'HESE' in alert_list:
            #print('HESE')
            is_hese = hese_alert_eval(message)
            if is_hese['pass_tight']:
                pass_hesev2_gold = True
            if is_hese['pass_loose']:
                pass_hesev2_bronze = True
                #print("HESE:",is_hese)
        if 'EHE' in alert_list:
            #print('EHE')
            is_ehe = ehe_alert_eval(message)
            if is_ehe['pass_tight']:
                pass_ehev2_gold = True
                #print("EHE:",is_ehe)

        frame['pass_gfu'] = icetray.I3Bool(pass_gfu)
        frame['pass_hesev2_gold'] = icetray.I3Bool(pass_hesev2_gold)
        frame['pass_hesev2_bronze'] = icetray.I3Bool(pass_hesev2_bronze)
        frame['pass_ehev2_gold'] = icetray.I3Bool(pass_ehev2_gold)
        frame['pass_gfu_gold'] = icetray.I3Bool(pass_gfu_gold)
        frame['pass_gfu_bronze'] = icetray.I3Bool(pass_gfu_bronze)


    return True


tray.Add(pass_alerts_check,Streams=[icetray.I3Frame.Physics])

tray.Add(I3HDFWriter,
         Output=outfile,
         Keys=['I3MCWeightDict',
               'pass_gfu',
               'pass_hesev2_gold',
               'pass_hesev2_bronze',
               'pass_ehev2_gold',
               'pass_gfu_gold',
               'pass_gfu_bronze',
           ],
         SubEventStreams=["InIceSplit"]
)

tray.AddModule("TrashCan", "YesWeCan")
tray.Execute()



# for file in infiles:
#     afile = dataio.I3File(file)
#     while afile.more():
#         events_read += 1
#         if pframe.Has('AlertNamesPassed'):
#             alert_list = pframe['AlertNamesPassed']
#             ## Skip those boring events that don't do ANYTHING.
#             if len(alert_list) == 0:
#                 continue
#             #if len(alert_list) > 1:
#             #    print(alert_list)
#             if pframe.Has('AlertShortFollowupMsg'):
#                 ev_json = json.loads(pframe['AlertShortFollowupMsg'].value)
#                 ## Pad the json to be like "I3Live"
#                 message = {'value': { 'data' : ev_json}}
#                 #print(message)            
#             else:
#                 if len(alert_list) > 0:
#                     ## Complain only if there should be a message from any alert
#                     print('Missing event dict!')

#         else:
#             print('Failed to find alert list!!')
#         if pass_gfu_gold or pass_gfu_bronze or pass_hesev2_gold or \
#            pass_hesev2_bronze or pass_ehev2_gold or pass_gfu:
#             # Save data for conversion to numpy array later
#             gfu_select.append(pass_gfu)
#             gfu_gold_select.append(pass_gfu_gold)
#             gfu_bronze_select.append(pass_gfu_bronze)
#             hese_gold_select.append(pass_hesev2_gold)
#             hese_bronze_select.append(pass_hesev2_bronze)
#             ehe_gold_select.append(pass_ehev2_gold)
#             if pframe.Has('I3MCWeightDict'):
#                 mc_wts = pframe['I3MCWeightDict']
#                 mc_one_wt.append(mc_wts['OneWeight'])
#                 mc_prim_E.append(mc_wts['PrimaryNeutrinoEnergy'])
#                 mc_prim_zen.append(mc_wts['PrimaryNeutrinoZenith'])
#                 mc_prim_azi.append(mc_wts['PrimaryNeutrinoAzimuth'])
#             else:
#                 print("No Weight Dict!")


# #print(mc_one_wt)
# print("Events cataloged:",len(mc_one_wt))
# print('Processed N_events:',events_read)
# arr = np.empty((len(mc_one_wt), ), dtype=[("PassGFU", np.bool),
#                                           ("PassGFUGold", np.bool),
#                                           ("PassGFUBronze", np.bool),
#                                           ("PassHESEGold", np.bool),
#                                           ("PassHESEBronze", np.bool),
#                                           ("PassEHEGold", np.bool),
#                                           ("PrimAzimuth",np.float),
#                                           ("PrimZenith",np.float),
#                                           ("PrimEnergy", np.float),
#                                           ("OneWeight", np.float)])



# arr["PassGFU"] = gfu_select
# arr["PassGFUGold"]=gfu_gold_select
# arr["PassGFUBronze"]=gfu_bronze_select
# arr["PassHESEGold"]=hese_gold_select
# arr["PassHESEBronze"]=hese_bronze_select
# arr["PassEHEGold"]=ehe_gold_select
# arr["PrimAzimuth"]=mc_prim_azi
# arr["PrimZenith"]=mc_prim_zen
# arr["PrimEnergy"]=mc_prim_E
# arr["OneWeight"]=mc_one_wt


# print("\t{0:6d} events".format(len(arr)))
# np.save(outfile, arr)
