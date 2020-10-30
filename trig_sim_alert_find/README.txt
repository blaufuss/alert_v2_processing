Oct 30, 2020 - EKB

HOW I PROCESSED SIM DATA TO ALERT LEVEL


1.  Find appropriate numu simprod samples

20878 - https://iceprod2.icecube.wisc.edu/dataset/ad3070f0bd4511e98bb6141877284d92
 E-2, 10k files 100 GeV - 10 PeV
21220 - https://iceprod2.icecube.wisc.edu/dataset/8cdbe0c2789411ea9ebf141877284d92
 E-1, 10k files 10 TeV - 50 PeV
21002 - https://iceprod2.icecube.wisc.edu/dataset/f01596d6107711ea9a4c141877284d92
 E-2, 10k files, 100 GeV - 10 PeV

2. Process these "triggered samples" to L1 filter level, saving only GFU, GrecoOnline, EHE/HESE, and ESTRES filter passing events.


Using /data/user/blaufuss/combo/V01-01-00
With a single diff:
Index: filterscripts/python/filter_globals.py
===================================================================
--- filterscripts/python/filter_globals.py	(revision 182686)
+++ filterscripts/python/filter_globals.py	(working copy)
@@ -198,6 +198,7 @@
                 (FSSFilter,1),
                 (FSSCandidate,0),
                 (VEFFilter,1),
+                (EHEFilter,1),
                 (LowUpFilter,1),
                 (SlopFilter, 1),
                 (FixedRateFilterName,1),
To make sure I can save the EHE filter events...

Processed with:
https://github.com/blaufuss/alert_v2_processing/tree/main/trig_sim_alert_find


Filter script is:

SimulationFiltering.py 

Only keeps filter passing:

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


HTCondor processing run, files ending in errors removed from output directory (few ~10 per batch
see:

ERROR (I3Module): AlertFollowup_small_followup: Exception thrown (I3Module.cxx:123 in void I3Module::Do(
void (I3Module::*)()))
Traceback (most recent call last):
  File "/data/user/blaufuss/alert_v2_processing/trig_sim_alert_find/SimulationFiltering.py", line 406, i
n <module>
    main(opts)
  File "/data/user/blaufuss/alert_v2_processing/trig_sim_alert_find/SimulationFiltering.py", line 382, i
n main
    tray.Execute()
  File "/data/user/blaufuss/combo/V01-01-00/build/lib/I3Tray.py", line 256, in Execute
    super(I3Tray, self).Execute()
  File "/data/user/blaufuss/combo/V01-01-00/build/lib/icecube/filterscripts/alerteventfollowup.py", line
 230, in generate_small_followup_message
    'zen'       : round(frame["OnlineL2_SplineMPE"].dir.zenith, 5),
KeyError: 'OnlineL2_SplineMPE'

(seems a corner case in alerteventfollowup that needs fixing....)

Condor config and DAG builder in Github repo with script.

Output files are:

/data/ana/realtime/alert_catalog_v2/sim_20878_alerts
/data/ana/realtime/alert_catalog_v2/sim_21220_alerts
/data/ana/realtime/alert_catalog_v2/sim_21002_alerts


3. Select alert events and build npy files for processing.

Now apply the realtime_XXX criteria to the filtered i3 files.
To do this, checked out realtime_XXX projects int my combo V01-01-00 build:

URL: http://code.icecube.wisc.edu/svn/meta-projects/realtime/releases/V20-07-00/realtime_ehe
URL: http://code.icecube.wisc.edu/svn/meta-projects/realtime/releases/V20-07-00/realtime_gfu
URL: http://code.icecube.wisc.edu/svn/meta-projects/realtime/releases/V20-07-00/realtime_hese
URL: http://code.icecube.wisc.edu/svn/meta-projects/realtime/releases/V20-07-00/realtime_tools

A few modifications where made to these to prevent some edge case crashes in the HESE FAR calculation
and missing dependencies for realtime_tools alert forwarding scripts (not used here)

blaufuss@cobalt05[../combo/V01-01-00/src]% svn diff realtime_hese/python/HESE_alerts_v2.py
Index: realtime_hese/python/HESE_alerts_v2.py
===================================================================
--- realtime_hese/python/HESE_alerts_v2.py	(revision 182870)
+++ realtime_hese/python/HESE_alerts_v2.py	(working copy)
@@ -124,11 +124,14 @@
     else:
         return None

-    recE = np.log10(E)
-    E_idx = np.searchsorted(E_dat['recE'], recE)-1
-    if E_idx < 0:
-        E_idx = 0    #prevent error for extremely small truncated E
-    return 10**E_dat['nuE'][E_idx]
+    if E is not None:
+        recE = np.log10(E)
+        E_idx = np.searchsorted(E_dat['recE'], recE)-1
+        if E_idx < 0:
+            E_idx = 0    #prevent error for extremely small truncated E
+        return 10**E_dat['nuE'][E_idx]
+    else:
+        return 0.0


 ## Actual evaluating function for the event
@@ -180,7 +183,8 @@

     # other quantities
     sig_ness   = locate_signalness(qtot, cos_zen, pass_tight, pass_loose)
-    exp_rate = locate_bkg_rate(qtot, pass_tight, pass_loose)
+    #exp_rate = locate_bkg_rate(qtot, pass_tight, pass_loose)
+    exp_rate = 1.0
     nu_energy = locate_Enu(truncated, pass_tight, pass_loose)


blaufuss@cobalt05[../combo/V01-01-00/src]% svn diff realtime_tools/python/__init__.py
Index: realtime_tools/python/__init__.py
===================================================================
--- realtime_tools/python/__init__.py	(revision 182870)
+++ realtime_tools/python/__init__.py	(working copy)
@@ -1,8 +1,8 @@
 import logging
 import sys

-from icecube.realtime_tools.receiver import make_receiver
-from icecube.realtime_tools.hs_sender_tools import gcn_hs_forwarder
+#from icecube.realtime_tools.receiver import make_receiver
+#from icecube.realtime_tools.hs_sender_tools import gcn_hs_forwarder
 from icecube.realtime_tools import config
 from icecube.realtime_tools import converter
 from icecube.realtime_tools import messaging


Script "process_filtered_sim.py" applies the alert criteria, and saves a summary npy file
of all events passing alerts. 

Some condor processing scripts combine_mc.sub,combine_npy.py, are provided to process all
and merge output from all  i3 files.


