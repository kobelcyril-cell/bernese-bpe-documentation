Check [[Quick start]] to start as quick as possible with the processing. Read the following inctructions for further details

PCFs:
To get everything you need, run the tool "Copy PCF", which can be found in [[Tools]].
Using this script, you can copy all components for the [[BPE_Workflows]].

PERL:
The perl-module [[RetryHelper]] is used in the following SCRIPTS:
- [[05_PID_Modules/SCRIPTS/ZDGNSS_PREPROCESSING/CODSPP_E|CODSPP_E]]
- [[GPSXTR_P]]
- [[05_PID_Modules/SCRIPTS/ZDGNSS_CODESCREENING/MRKOB__E|MRKOB__E]]
- [[05_PID_Modules/SCRIPTS/ZDGNSS_FINISH/STDPRE|STDPRE]]
The perl-module (RetryHelper.pm) fis located in ~/ZDGNSS_RUN/perl.

PYTHON:
Several python scripts are used in the processing. If you want to modify them, please copy them first and adjust the paths accordingly in the following SCRIPTS:
- [[STATION_SELECTION]]
	- ~/ZDGNSS_RUN/python
- [[CHECK_SAT_CLOCKS]]
	- ~/ZDGNSS_RUN/python ([[check_clk_completeness]])

MATLAB:
Several matlab scripts are used in the processing. In case of corrections/adjustments needed, copy them to your desired directory and adjust the paths in the corresponding SCRIPTS:
- [[CMP_LAPACK]]
	- ~/ZDGNSS_RUN/matlab
- [[STATION_SELECTION]]
	- ~/ZDGNSS_RUN/matlab

PROJECTS:
Currently two projects are used:
- PHACOR_CK (used in [[ZD_IAR_NLB]])
- ADDNEQ2 (used in [[06_Bernese_Programs/ZDGNSS_SOL/FIN/ZD_FIN|ZD_FIN]])

