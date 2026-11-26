# Software and setup

## Prepare the GPSUSER

Use **Copy PCF** in the [[Operations_and_Tools/Toolbox and maintenance.md|toolbox]] to copy the PCF and its SCRIPT and OPT components into your GPSUSER. The tool checks for conflicts before copying.

## Check the processing dependencies

### Perl

The scripts `ZD_CODSPP_E`, `ZD_MRKOB__E` and `ZD_STDPRE` use `RetryHelper.pm` from `~/ZDGNSS_RUN/perl`. See [[Operations_and_Tools/Monitoring and recovery.md|Monitoring and recovery]] for the retry functions and usage.

### Python

If you need to modify a Python helper, make a copy first. Update its path in the corresponding script. The documented entry points are `STATION_SELECTION`, `CHECK_SAT_CLOCKS`, `ZD_HELMR1_VS`, `plotCOMPAR` and `plotORBVER`.

### MATLAB

For local changes, copy the MATLAB helpers and update their paths in `ZD_CMP_LAPACK` and `ZD_STATION_SELECTION` where applicable.

### Project-specific Bernese programs

The project versions have their own entries for [[System_Overview/PHACOR CK.md|PHACOR phase correction]], [[System_Overview/ADDNEQ2 LAPACK.md|ADDNEQ2 with LAPACK]] and [[System_Overview/GPSEST clock grid.md|the GPSEST satellite-clock grid]]. Each entry identifies the project implementation, input settings or build paths relevant to inspection.
