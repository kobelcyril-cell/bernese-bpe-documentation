# Monitoring and recovery

## Check a running BPE

- **Monitor BPE (`monitor_bpe`).** Open the campaign monitor from the [[Operations_and_Tools/Toolbox and maintenance.md|toolbox]]. It works like `tkbpe` and can monitor different campaigns.
- **error_watch.** Monitor `.RUN` files and send status messages via Telegram. Set up your own notifications using `error_watch_manual.txt` before starting `error_watch.sh`. The configuration also uses `IGNORE.LIST` and `WATCH.LIST`. Copying an existing installation with its notification settings can send alerts to the previous recipient.

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
