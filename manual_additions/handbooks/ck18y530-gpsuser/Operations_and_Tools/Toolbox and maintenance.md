# Toolbox and maintenance

Open the Python toolbox from the project tools directory.

```bash
cd ~/ZDGNSS_RUN/Tools
python3 Tools.py
```

## Prepare or inspect a GPSUSER

- **Copy PCF (`get_my_pcf`).** Copy a PCF and its SCRIPT and OPT components between GPSUSERs, including across accounts. The tool checks for conflicts to prevent overwrites.
- **PCF Viewer (`pcf_viewer`).** Select a PCF and then a job row to see its input file and script. Select a PCF variable to highlight its uses in those files. Use the **Locked** button before editing the script. PID notes are saved as `PCFFILENAME_help.json` in the PCF directory.
- **Find variables in BPE (`find_variables_in_bpe`).** Search PCFs for a variable such as `$(FIN)`.
- **Search file in BPE (`search_file_in_bpe`).** Look for a file pattern across PCFs. Example search strings are `$(FIN)_$YSS+0` and `$(FIN)_$YSS+0.STD`.
- **Filetracer (`filetracer`).** Experimental tool for tracing file accesses and modifications by scripts.

## Clean up after a test

- **Clean GPSUSER (`clean_gpsuser`).** Identify unused option directories and scripts. Start with analysis to review the results. The cleanup mode moves unused items.
- **Clean subfolders (`clean_subfolders`).** Clean a campaign when reusing it for a test.
- **Clean residuals (`clean_residuals.py`).** Use after a one-day test with normal file deletion disabled. It deletes the files that `DEL_RES_1D` would have deleted. The tool is in `/storage/homefs/ck18y530/python`. Use `python3 clean_residuals.py -h` to see an example invocation.
