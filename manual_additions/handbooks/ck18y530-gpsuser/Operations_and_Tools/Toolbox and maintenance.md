# Toolbox and maintenance

The toolbox is a tabbed PyQt5 launcher. The standalone copy is in `~/Tools`. A second copy is bundled with the [[Controllers/ZDGNSS run package.md|ZDGNSS run package]] under `~/ZDGNSS_RUN/Tools`. To open the standalone copy, run the launcher from its directory.

```bash
cd ~/Tools
python3 Tools.py
```

Both copies have application code in `programs/` and individual help pages in `help/`. The bundled copy also has the **PCF File History** tab described below.

## Prepare or inspect a GPSUSER

- **Copy PCF (`get_my_pcf`).** Select one or more PCFs and the source and destination GPSUSER. The tool builds a copy plan for the PCFs, their SCRIPT and OPT dependencies and CFG files referenced by `V_PCFCONFIG`. It deduplicates shared dependencies, flags missing sources and blocks destination conflicts before copying.
- **PCF Viewer (`pcf_viewer`).** Select a PCF and then a job row to see its input file and script. Select a PCF variable to highlight its uses in those files. Use the **Locked** button before editing the script. PID notes are saved as `<PCF_NAME>_help.json` in the PCF directory.
- **Find variables in BPE (`find_variables_in_bpe`).** Search for a case-sensitive string such as `$(FIN)` in the INP files belonging to OPT directories referenced by the PCFs. The results identify each PCF, matching files and shared OPT directories.
- **Search file in BPE (`search_file_in_bpe`).** Search INP values for a pattern, look up the extension in `MENU_EXT.INP` when applicable and identify PCFs using the matching option directory. Example search strings are `$(FIN)_$YSS+0` and `$(FIN)_$YSS+0.STD`.
- **File Tracer (`filetracer`).** Statically trace file accesses and modifications in Bernese Perl scripts. It groups detected patterns and helps locate reads, writes, moves and deletions.
- **PCF File History.** In the bundled toolbox, select a filename or template and one or more PCFs. The tool shows potential readers and writers by PID and follows known WAIT dependencies. Dynamic paths and runtime branches can leave gaps in this static view.

## Read run status

**BPE Monitor (`monitor_bpe`)** scans `<partition>/<campaign>/BPE` for `.RUN` files and shows their status and details. It is a viewer. Use the launcher to start processing and [[Operations_and_Tools/Monitoring and recovery.md|Monitoring and recovery]] for automated notifications.

## Clean up after a test

- **Clean GPSUSER (`clean_gpsuser`).** Compare PCF references with SCRIPT and OPT contents to detect unused or missing items. Review the analysis first. Cleanup moves eligible unused items to `GRAVEYARD`.
- **Clean campaign (`clean_subfolders`).** Review the keep lists and use **Preview** to inspect the planned changes. The confirmed cleanup can remove files and directories from the selected campaign.
- **Clean residuals (`clean_residuals.py`).** Use after a one-day test with normal file deletion disabled. It deletes the files that `DEL_RES_1D` would have deleted. The tool is in `/storage/homefs/ck18y530/python`. Use `python3 clean_residuals.py -h` to see an example invocation.
