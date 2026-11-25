package RetryHelper;
use strict;
use warnings;
use lib "$ENV{BPE}";
use bpe_util;
use Exporter 'import';

our @EXPORT_OK = qw(
    run_with_retry
    run_with_retry_noerror
    run_retry_goto
);
# ----------------------------------------------------------------------------
# run_with_retry($bpe, $PGMNAM, [$max_retries, $retry_delay])
#
# Führt ein Programm mehrfach aus (klassischer Retry-Mechanismus).
# ----------------------------------------------------------------------------
sub run_with_retry {
  my ($bpe, $PGMNAM, $max_retries, $retry_delay) = @_;
  $max_retries //= 3;
  $retry_delay //= 10;

  my $success = 0;
  my $retry_needed = 0;
  my $logfile = "$ENV{U}/SCRIPT/retry.log";

  for (my $attempt = 1; $attempt <= $max_retries; $attempt++) {
    print "==== Attempt $attempt/$max_retries for $PGMNAM ====\n";

    my ($status, $err);
    {
      local $@;
      eval {
        $status = $bpe->RUN_PGMS($PGMNAM);
        1;
      } or do {
        $err = $@ || "Unknown exception";
      };
    }

    if (defined $err && $err ne '') {
      warn "==== $PGMNAM died/raised exception on attempt $attempt: $err ====\n";
    } elsif (defined $status && $status == 0) {
      print "==== $PGMNAM succeeded on attempt $attempt ====\n";
      $success = 1;
      last;
    } else {
      my $st_text = defined $status ? $status : 'undef';
      warn "==== $PGMNAM returned failure status on attempt $attempt: $st_text ====\n";
    }

    if ($attempt < $max_retries) {
      $retry_needed = 1;
      print "Retrying in $retry_delay seconds...\n";
      sleep $retry_delay;
    }
  }

  unless ($success) {
    _write_retry_log($logfile, $bpe, $PGMNAM, "FAILED_AFTER_$max_retries");
    die "ERROR: $PGMNAM failed after $max_retries attempts.\n";
  }

  if ($retry_needed) {
    _write_retry_log($logfile, $bpe, $PGMNAM, "RETRY_NEEDED");
  }
}

# ----------------------------------------------------------------------------
# run_with_retry($bpe, $PGMNAM, [$max_retries, $retry_delay])
#
# Führt ein Programm mehrfach aus (klassischer Retry-Mechanismus).
# Beendet ordentlich, selbst wenn Prgramm einen Fehler gibt.
# ----------------------------------------------------------------------------
sub run_with_retry_noerror {
  my ($bpe, $PGMNAM, $max_retries, $retry_delay) = @_;
  $max_retries //= 3;
  $retry_delay //= 10;

  my $success = 0;
  my $retry_needed = 0;
  my $last_error = '';

  my ($day,$outdir,$pid,$pcf) =
      $bpe->getKeys('$YD+0','DIR_OUT','PID','PCFFIL');
  my $logfile = "${outdir}../MSC/retry.log";

  for (my $attempt = 1; $attempt <= $max_retries; $attempt++) {

    print "==== Attempt $attempt/$max_retries for $PGMNAM ====\n";

    my ($status, $err);

    {
      local $@;
      eval {
        $status = $bpe->RUN_PGMS($PGMNAM);
        1;
      } or do {
        $err = $@ || "Unknown exception";
      };
    }

    if (defined $err && $err ne '') {

      $last_error = "Exception: $err";
      warn "$last_error\n";

    }
    elsif (defined $status && $status == 0) {

      print "==== $PGMNAM succeeded ====\n";
      $success = 1;
      last;

    }
    else {

      my $st = defined $status ? $status : 'undef';
      $last_error = "Return status: $st";
      warn "==== $PGMNAM failed with status $st ====\n";

    }

    if ($attempt < $max_retries) {
      $retry_needed = 1;
      print "Retrying in $retry_delay seconds...\n";
      sleep $retry_delay;
    }
  }

  if ($success) {

    if ($retry_needed) {
      _write_retry_log($logfile, $bpe, $PGMNAM, "RETRY_NEEDED");
    }

    return 1;
  }

  _write_retry_log(
      $logfile,
      $bpe,
      $PGMNAM,
      "FAILED_AFTER_${max_retries}: $last_error"
  );

  print "==== $PGMNAM failed after $max_retries attempts. Continuing without error. ====\n";

  return 0;
}
# ----------------------------------------------------------------------------
# run_retry_goto($bpe, $PGMNAM, $param1, $param2)
#
# Führt ein Bernese-Programm aus und springt bei erstem Fail zu NEXTJOB.
# Beim zweiten Fail: Flag löschen und die().
# ----------------------------------------------------------------------------
sub run_retry_goto {
  my ($bpe, $PGMNAM, $param1, $param2) = @_;

  my ($day,$outdir,$pid,$pcf) = $bpe->getKeys('$YD+0','DIR_OUT','PID','PCFFIL');
  my $logfile = "${outdir}../MSC/retry_goto.log";
  my $flagfile = "${outdir}../MSC/RETRY_GOTO_${day}_${pid}_${pcf}.FLG";

  my ($status, $err);
  {
    local $@;
    eval {
      $status = $bpe->RUN_PGMS($PGMNAM);
      1;
    } or do {
      $err = $@ || "Unknown exception";
    };
  }

  if (defined $err && $err ne '') {
    warn "==== $PGMNAM died/raised exception: $err ====\n";

    if ($param1 eq "NEXTJOB") {
      if (-e $flagfile) {
        # Zweiter Fail -> Flag löschen + harter Abbruch
        unlink $flagfile or warn "Could not delete flag file $flagfile: $!";
        _write_retry_log($logfile, $bpe, $PGMNAM, "FAILED_AFTER_RETRY");
        die "PID $pid failed again after retry. Stopping execution.\n";
      } else {
        # Erster Fail -> Flag setzen und Retry starten
        open(my $fh, '>', $flagfile) or die "Cannot create retry flag $flagfile: $!";
        print $fh time();
        close($fh);

        _write_retry_log($logfile, $bpe, $PGMNAM, "RETRY_TRIGGERED_TO_$param2");
        print "PID $pid failed – retrying from PID $param2 ...\n";
        prtGoto($bpe, $param2);
      }
    }
  }
  elsif (defined $status && $status == 0) {
    print "==== $PGMNAM succeeded ====\n";
    _write_retry_log($logfile, $bpe, $PGMNAM, "SUCCESS");

    if (-e $flagfile) {
      unlink $flagfile or warn "Could not delete flag file $flagfile: $!";
    }
  }
  else {
    warn "==== $PGMNAM returned undefined or nonzero status ====\n";
  }
}

# ----------------------------------------------------------------------------
# interne Hilfsfunktion: schreibt Logeinträge
# ----------------------------------------------------------------------------
sub _write_retry_log {
  my ($logfile, $bpe, $PGMNAM, $status) = @_;
  my ($day,$outdir,$pid,$pcf) = $bpe->getKeys('$YD+0','DIR_OUT','PID','PCFFIL');
  my $timestamp = scalar localtime;

  if (open my $fh, '>>', $logfile) {
    print $fh "$timestamp | $PGMNAM | DAY=$day | PCF=$pcf | PID=$pid | $status\n";
    close $fh;
  } else {
    warn "Could not open retry log $logfile: $!";
  }
}

1;
