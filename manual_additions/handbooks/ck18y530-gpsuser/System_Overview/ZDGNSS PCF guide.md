# ZDGNSS PCF guide

This guide covers the 18 `ZDGNSS_*.PCF` files in `~/GPSUSER/PCF` on Sedna. Open a PCF link to inspect its job PIDs, scripts, option directories and WAIT dependencies. Several workflows also use `ZD_STATUS` to wait for or write a stage flag. Check the PCF variables for the expected flag and configuration when diagnosing a hand-off.

## Prepare and screen observations

- [[ZDGNSS_PREPARATION.PCF]] checks the campaign, copies observations and reference files, selects the station network, prepares a priori coordinates and orbits, and screens station and satellite availability.
- [[ZDGNSS_PREPROCESSING.PCF]] runs initial observation preprocessing, computes code weights and performs station-wise satellite-clock checks.
- [[ZDGNSS_CODESCREENING.PCF]] generates code-based orbits and code residuals, checks stations, marks bad observations, extracts OSBs and produces code-only clocks.
- [[ZDGNSS_PHASESCREENING.PCF]] preprocesses phase data and iterates residual screening. It checks stations and observations, adjusts thresholds and weights, and combines clocks.

## Estimate the solution and resolve ambiguities

- [[ZDGNSS_SOL_FA.PCF]] sets up and combines normal equations, with optional LEO NEQs. It checks the datum, supports a large-system or pre-eliminated-clock path and produces clocks, orbits and statistics. It selects the `FA` configuration.
- [[ZDGNSS_AR.PCF]] estimates wide-lane and narrow-lane biases and ambiguities. It checks bias estimates, updates the orbit and combined bias file, and records resolved ambiguities in observation files.
- [[ZDGNSS_SOL_IA.PCF]] uses the same job structure as the FA solution with the `IA` configuration.
- [[ZDGNSS_SOL_FINAL.PCF]] uses that solution structure with the `FINAL` configuration.
- [[ZDGNSS_PPP.PCF]] prepares inputs and clocks, screens and solves PPP station by station, merges OSB and coordinate files, and writes a processing summary.
- [[ZDGNSS_LEONEQ.PCF]] selects and checks LEO data, prepares and executes parallel LEO NEQ jobs, and checks that the NEQs exist. The solution PCFs have a separate job to add LEO NEQs when required.

## Finish, combine three-day arcs and densify clocks

- [[ZDGNSS_FINISH.PCF]] creates final PRE orbits, satellite attitude information and processing summaries. It can compare full and pre-eliminated-clock solutions. It waits for `IA` and writes `FINISH_R`.
- [[ZDGNSS_FINISH_FINAL.PCF]] performs the same finishing stages with the `FINAL` configuration. It waits for `IA_F` and writes `FINISH_F`.
- [[ZDGNSS_3D.PCF]] prepares three-day inputs, generates the long-arc solution using the LAPACK ADDNEQ2 jobs, creates orbit and clock products, and saves results. It selects the `3D` configuration.
- [[ZDGNSS_3D_FINAL.PCF]] uses the same three-day job structure with the `3DF` configuration.
- [[ZDGNSS_CLKDEN.PCF]] prepares receiver clocks and troposphere estimates, merges and combines clock products, changes the clock reference, and produces high-rate clocks and a satellite-only clock product.
- [[ZDGNSS_CLKDEN_FINAL.PCF]] uses the same densification structure with the `CLKDENF` configuration. The other variant selects `CLKDEN`.

## Validate and compare

- [[ZDGNSS_VALSOL.PCF]] prepares solution data for coordinate repeatability and Helmert checks, orbit verification, and station and satellite diagnostics. Its final jobs generate plots and concatenate validation output.
- [[ZDGNSS_CMPSOL.PCF]] prepares solution data, compares ERP, orbit and clock products, runs COMPAR2 and a Helmert comparison, and combines their summaries.

Use the [[Controllers/Perl wrappers and PCFs.md|Perl wrapper reference]] to find the entry point for a stage and [[Operations_and_Tools/Quality checks and plots.md|Quality checks and plots]] to choose a diagnostic after the run.
