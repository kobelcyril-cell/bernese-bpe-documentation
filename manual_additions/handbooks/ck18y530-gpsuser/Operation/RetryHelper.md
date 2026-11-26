A perl-Module which allows to rerun a specific Bernese Program. Use it for example like this:
First import the module:
use lib "$ENV{HOME}/ZDGNSS_RUN/perl;
use RetryHelper qw(run_with_retry);

Example:
    my $PGMNAM = "SATMRK";
    run_with_retry($bpe, $PGMNAM,10);

The module can be found in ~/ZDGNSS_RUN/perl

Multiple functions are available in this module:
- run_with_retry
- run_with_retry_noerror
	- Used in [[05_PID_Modules/SCRIPTS/ZDGNSS_PPP/CODSPP_E|CODSPP_E]]
- run_retry_goto

You may adapt the path for the log-file in the perl-module (line 25).