Check [[Quick start]] to start as quick as possible with the processing. Read the following instructions for further details

PCFs:
To get everything you need, run the tool "Copy PCF", which can be found in [[Tools]].
Using this script, you can copy all components for the BPEs.

Perl-scripts:
In the ZDGNSS-BPE-processing the perl-module [[RetryHelper]] is used
in the following SCRIPTS:
- ZD_CODSPP_E
- ZD_MRKOB__E
- ZD_STDPRE
The perl-module (RetryHelper.pm) is located in ~/ZDGNSS_RUN/perl.

Python-scripts:
Several python scripts are used in the processing. If you want to modify them, please copy them first and adjust the paths accordingly in the following Scripts:
- [[STATION_SELECTION]]
- [[CHECK_SAT_CLOCKS]]
- [[ZD_HELMR1_VS]]
- [[plotCOMPAR]]
- [[plotORBVER]]

Matlab-scripts:
Several matlab scripts are used in the processing. In case of corrections/adjustments needed, copy them to your desired directory and adjust the paths in the corresponding SCRIPTS:
- [[ZD_CMP_LAPACK]]
- [[ZD_STATION_SELECTION]]

Project versions of Bernese programs:
Currently some project versions are used:
- PHACOR_CK
- ADDNEQ2_LAPACK
- GPSEST_CLOCK_GRID

