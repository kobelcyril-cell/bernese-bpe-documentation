# Quality checks and plots

## Choose a plot

The following plotting scripts are documented in `/storage/homefs/ck18y530/python`.

- **Processing statistics.** `generate_processing_plots.py` provides a GUI for plotting run statistics from `PROCESSING_$YD+0` files.
- **Solution validation.** `generate_validation_plots.py` plots validation results. See [[ZDGNSS_VALSOL.PCF]] for the ZDGNSS validation jobs.
- **Solution comparison.** `generate_comparison_plots.py` plots comparison summaries. See [[ZDGNSS_CMPSOL.PCF]] for the ZDGNSS comparison jobs.
- **Repeatability differences.** `plot_repeatabilites_differences.py` compares two solutions using validation results. The filename uses the spelling shown here.

## Investigate exclusions

- **Satellites.** `satellite_problems_plot.py` analyses reasons for satellite exclusions. Give it the campaign’s `MSC` directory. By default, it writes its outputs to the current working directory.
- **Stations.** The station-exclusion notes list `Plot_excluded_stations.py` and give the following invocation under the filename `summarize_excluded_stations.py`. Check the filename in your installation. The input is the campaign’s `MSC` directory.

```bash
python3 ~/python/summarize_excluded_stations.py "$R/CK_ZDGNSS/MSC"
```

## Helpers called by the processing chain

- **Clock completeness.** `check_clk_completeness` is used by `CHECK_SAT_CLOCKS`.
- **Stations used for validation.** `extract_fix_stations` extracts stations with flag `W` or `I` from a `.CRD` file. See the `ZD_HELMR1_VS` job in [[ZDGNSS_VALSOL.PCF]] for the related Helmert comparison.
