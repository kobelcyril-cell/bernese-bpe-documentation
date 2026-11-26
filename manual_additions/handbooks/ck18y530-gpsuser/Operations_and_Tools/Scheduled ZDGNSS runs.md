# Scheduled ZDGNSS runs

The active wrappers in `~/bash_scripts/ZDGNSS` prepare the Bernese environment and launch processes in the background. They set `BPE`, `AUTO` and `EXE` and redirect output to log files. The older per-stage cron wrappers are in `GRAVEYARD/`.

## Daily processing chain

`run_zdgnss.sh` calls `~/perl/ZDGNSS/bpe_worker_routine.py` with `master_config.json`. It writes a top-level log named `bpe_workerYYDDD.log` under `~/perl/ZDGNSS/LOGR`. The worker builds an ordered list of enabled jobs. Each job's `days_ago` is applied to the reference date, and `n` sets its session count. A real run creates a timestamped directory under the configured `log_base` with `bpe_launcher.log` and the individual job logs.

The worker treats a nonzero exit code or an `error` match in a job log as a failure. It normally stops at the first failed job. `continue_after_error` controls whether to continue, and `global_wait` sets the delay between jobs.

Use the worker's `--dry-run` option to check the resulting commands without launching jobs or creating run logs. Use a Python environment compatible with the routine worker.

```bash
cd ~/perl/ZDGNSS
python3 bpe_worker_routine.py --config master_config.json --dry-run
```

`--date` changes the reference day, `--days-ago` and `--n` override job session settings, and `--jobs` selects wrapper filenames while preserving configuration order.

## Validation and comparison wrappers

- `run_zd_val_rapid_1d_cron.sh` calls `val_rapid_1d.pl` with `-R=1` for the rapid one-day validation and writes `VALSOL_1DAY_RAPIDYYDDD.log`.
- `run_zd_cmpsol_mgex_1day_rapid_cron.sh` calls `cmpsol_mgex.pl` with `-R=5` for the MGEX comparison and writes `CMPSOL_MGX_1DAY_RAPIDYYDDD.log`. The offset in the actual command is five days.

Both validation and comparison wrappers use the launch date in the log suffix. When checking a specific session, use the invoked wrapper's offset and the session reported in the logs.
