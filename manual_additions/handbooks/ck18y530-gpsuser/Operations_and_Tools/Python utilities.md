# Python utilities

The scripts in `~/python` provide diagnostics and maintenance for Bernese campaigns. The sections below group the utilities by inputs and use. The project run package also has selected Python copies under `~/ZDGNSS_RUN/python`.

## Check solutions and processing products

- `generate_processing_plots.py` reads `PROCESSING_*` logs and plots run statistics. `generate_validation_plots.py` and `generate_comparison_plots.py` visualise validation and comparison results.
- `plot_repeatabilites.py`, `plot_repeatabilites_differences.py` and `plot_repeatabilities_sum.py` summarise or compare repeatability statistics. The differences tool compares common stations and the north, east and up components from two selected solutions.
- `satellite_problems_plot.py` reads problem-check blocks from campaign processing logs. `summarize_excluded_stations.py` counts each excluded station at most once per `PROCESSING_*` file across the selected campaign MSC directories and writes a PNG.
- `check_clk_completeness.py` takes a clock file and an output text file. It reports the completeness of the 300-second satellite-clock epochs.
- `extract_leo_results.py` extracts and plots LEO quality statistics, including a posteriori RMS and ambiguity-resolution results.
- In `~/ZDGNSS_RUN/python/validation_plot`, `plot_compar2.py` reads original COMPAR2 reports from a campaign OUT directory and plots repeatability. `plot_orb_ver.py` reads a standalone ORB_VER LST summary and can use the daily archive for dates. See [[Operations_and_Tools/Quality checks and plots.md|Quality checks and plots]] for the corresponding processing references.

## Extract station information and prepare ancillary files

- `extract_fix_stations.py` extracts stations flagged `W` or `I` from a coordinate file for validation.
- `StationNetwork/get_final_stations.py` reads a coordinate file and selects stations with flag `A` or `W`. `StationNetwork/extract_geos_letters.py` reads matching observation-file headers and reports GNSS system letters.
- `combine_erp.py` combines daily ERP files matching a supplied filename prefix into one output file.
- `copy_crx.py` copies a configured CRX to a configured shared destination using atomic replacement. Confirm the configured source and target in the script before using it.

## Inspect or change inputs and clean up

- `check_campaign_paths.py` checks entries in the `CAMPAIGN` list of an INP file and can write a separate corrected file. It defaults to `AIUB_CMP.INP`.
- `check_perl_uninit.py` checks Perl syntax without a normal run of the script. It accepts files or directories and a Perl executable override.
- `inp_string_replacer.py` replaces literal text in selected subdirectories' INP files. `search_inp_used_systems.py` sets `USE_*` constellation flags in INP files under selected direct child directories.
- `correct_log_file.py` edits a selected occurrence in a log after an interactive section and count check.
- `clean_residuals.py` applies the one-day residual cleanup rules. `cleanup_processing.py` provides a GUI preview and requires confirmation before deleting files. Review the selected campaign and file set before committing a cleanup.
