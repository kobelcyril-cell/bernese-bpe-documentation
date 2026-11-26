# Monitoring and recovery

## Check a running BPE

- **Monitor BPE (`monitor_bpe`).** Open the campaign monitor from the [[Operations_and_Tools/Toolbox and maintenance.md|toolbox]]. It works like `tkbpe` and can monitor different campaigns.
- **error_watch.** Use the monitor below for Telegram alerts from selected logs.

## Send log alerts with error_watch

`~/error_watch/error_watch.sh` scans the files listed in `WATCH.LIST` for `error` and messages of the form `Session <number>: finished`. It also sends a warning when a watched file is missing. Each matching alert can include the file and the matched log line.

### Files and modes

- `WATCH.LIST` takes one absolute log path per line, typically a campaign `.RUN` file. Blank lines and lines starting with `#` are skipped.
- `IGNORE.LIST` takes `/absolute/path/to/log|substring`. The path must match the watched file, and the installed script compares the substring literally and case-sensitively. The scan for error and session patterns itself is case-insensitive.
- `MODE=NEW` is the default. `error_watch.STATE` records reported path and line-number pairs to suppress repeated alerts for those lines. A replaced or rotated log can reuse line numbers, so account for the state file when troubleshooting missing alerts.
- `MODE=A` reports matching lines on each scan and bypasses the recorded-line check.

### Prepare a scheduled check

Start from the directory containing `WATCH.LIST`, `IGNORE.LIST` and `error_watch.STATE`. The script resolves these names relative to its working directory, so set that directory explicitly if you schedule the check. Use `error_watch_manual.txt` for the Telegram setup and configure your own recipient before running it. Telegram receives matched log lines, so watch files whose contents are suitable for that notification channel.

## Record a BPE jump

`JumpLogger.pm` records jumps in a log file. Copy it from `ck18y530/GPSUSER/SCRIPT` into your SCRIPT directory and set the log path in the module. Add the following import near the start of the script after `@ISA`.

```perl
use lib "$ENV{HOME}/GPSUSER/SCRIPT";
use JumpLogger qw(logJump);
```

Call `logJump` immediately before the existing `prtGoto` call.

```perl
logJump($bpe, $param2);
prtGoto(\$bpe, $param2);
```

The module also provides `jumpAndLog`. The original notes leave its current behaviour unverified.

## Retry a Bernese program

`RetryHelper.pm` is in `~/ZDGNSS_RUN/perl`. The module provides `run_with_retry`, `run_with_retry_noerror` and `run_retry_goto`. This example shows how to retry `SATMRK`.

```perl
use lib "$ENV{HOME}/ZDGNSS_RUN/perl";
use RetryHelper qw(run_with_retry);

my $PGMNAM = "SATMRK";
run_with_retry($bpe, $PGMNAM, 10);
```

The setup notes list the scripts that use this module. `CODSPP_E` uses `run_with_retry_noerror`. The retry log path can be adjusted in the module.
