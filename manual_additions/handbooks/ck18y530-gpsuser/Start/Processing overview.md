# Zero-difference GNSS processing

This handbook describes how to start a ZDGNSS run, follow it through the Bernese Processing Engine (BPE), and inspect the results. It covers the controllers, processing stages and utilities used by this GPSUSER.

## Where to begin

- **Run a session** with the [[Start/Run your first session.md|quick start]]. Use [[Start/Software and setup.md|software and setup]] to prepare a GPSUSER.
- **Follow a processing stage** in the [[System_Overview/Processing architecture.md|processing architecture]]. The [[Controllers/Perl wrappers and PCFs.md|wrapper reference]] shows the PCF behind each listed stage.
- **Investigate a run** using [[Operations_and_Tools/Monitoring and recovery.md|monitoring and recovery]], then [[Operations_and_Tools/Quality checks and plots.md|quality checks and plots]].
- **Find supporting tools** in the [[Operations_and_Tools/Toolbox and maintenance.md|toolbox and maintenance reference]].

## How a run is launched

The Python controller schedules Perl wrappers. Each wrapper starts a specific PCF. The PCF defines the BPE jobs and their dependencies. You can also run an individual wrapper or start a BPE directly from the Bernese menu.
