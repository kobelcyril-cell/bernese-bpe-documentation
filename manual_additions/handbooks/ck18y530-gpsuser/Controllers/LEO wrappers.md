# LEO Perl wrappers

The launchers in `~/perl/LEO` separate orbit determination for a selected low Earth orbiter from the creation of normal equations for use in the ZDGNSS workflow.

## Orbit determination with leopod.pl

`leopod.pl` starts `LEOPOD.PCF` for the spacecraft selected with `-leo=`. Supply the campaign partition with `-lw=`, the campaign with `-camp=` and the first day with `-yyddd=`. `-n=` controls the number of sessions.

The default configuration is `leopod_leos.conf` next to the wrapper. The `-config=` option selects a different configuration file. Each spacecraft section provides spacecraft identifiers and mission-specific antenna, attitude, sampling and data directory settings. Check the selected section before comparing runs for different spacecraft.

## ZDGNSS normal equations with leoneq.pl

`leoneq.pl` starts [[ZDGNSS_LEONEQ.PCF]]. That PCF checks and selects LEO inputs, sets up parallel NEQ jobs and verifies that they produced NEQs. The ZDGNSS solution workflow can then include those NEQs when the corresponding configuration enables them.

Use `-h` on the wrapper for its session options. `LEO_INCLUDE.DAT` is also present alongside the LEO wrappers. The [[System_Overview/ZDGNSS PCF guide.md|PCF guide]] shows the LEO and solution processing stages together.
