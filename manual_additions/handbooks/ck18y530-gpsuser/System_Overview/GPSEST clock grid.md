# GPSEST satellite-clock grid

The project build in `~/GPSEST_CLOCK_GRID` can restrict **satellite-clock parameter creation** to an epoch grid. It uses the parameter epoch, reference epoch and tolerance to decide whether a clock parameter is on the grid. The grid option controls parameter creation during estimation.

## Input settings

Set the clock-grid options in the project `FOR/GPSEST.INP` template or the corresponding input panel.

- `CLKS_GRID` enables the feature. The template defaults to `0`.
- `CLKS_GRID_STEP` sets the interval in seconds. The default is `300`.
- `CLKS_GRID_REF` sets the reference MJD in the same time scale as the parameter epochs. The default `0` aligns a 300-second grid with midnight.
- `CLKS_GRID_TOL` sets the epoch tolerance in seconds. The default is `0.001`. It must be positive and smaller than half the interval.
- `CLKS_GRID_LOG` prints the created clock epochs and clocks passed to NEQ saving when enabled.

With the grid enabled, the implementation requires satellite-clock estimation (`CLOCKS = 1`), `PRE24 = NO` and `OPTELI(24) = 0` after option checking. The print file reports the interval, reference MJD and tolerance. Use these lines and the optional clock log to confirm which settings the run applied.

## Sources and build

`FOR/GPSCLOCKGRID.f90` contains the grid test, epoch counting and option validation. `FOR/compile_gpsest_grid.sh` compiles the clock-grid module and the affected GPSEST routines plus the main program using `ifort`. It writes `EXE_IFC/GPSEST`. The folder also contains `EXE_GNU/GPSEST`. Check the actual executable and input panel selected by your run when comparing results.

See the [[System_Overview/ZDGNSS PCF guide.md|PCF guide]] for the separate clock-densification workflows and the [[Operations_and_Tools/Python utilities.md|Python utilities]] for post-run clock-completeness checks.
