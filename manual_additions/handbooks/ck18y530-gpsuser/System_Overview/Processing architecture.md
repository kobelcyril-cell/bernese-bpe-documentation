# Processing architecture

## From campaign to PCF

1. **Python controller.** Choose the campaign, partition and sessions, then arrange the jobs you want to run. See [[Controllers/Python run controller.md|Python run controller]].
2. **Perl wrappers.** Each wrapper launches one PCF. Use the [[Controllers/Perl wrappers and PCFs.md|wrapper reference]] to identify the corresponding workflow or start a stage from the command line.
3. **Bernese BPE.** Follow the selected PCF to see its jobs, dependencies, scripts and options. The PCF page shows the process table and any WAIT dependencies.

## How to read the workflow

- **Prepare the run.** The wrapper reference starts with preparation and preprocessing, then lists code and phase screening.
- **Follow the solution stages.** It lists the FA, AR, IA, finish, 3D and PPP steps together with their PCFs.
- **Find final and clock stages.** Final IA, finish and 3D each have a separate wrapper. Clock densification has its own wrapper as well.

The wrapper list is a reference for locating each stage. To see the job sequence for a particular run, inspect **Dry-Run** in the Python controller. To see dependencies within one PCF, open its process table.

## Inspect the results

Use the processing statistics for an overview of the run, validation or comparison plots for the corresponding solution checks, and campaign exclusions for station or satellite diagnostics. The [[Operations_and_Tools/Quality checks and plots.md|quality checks]] page points to the tools and inputs for each task.
