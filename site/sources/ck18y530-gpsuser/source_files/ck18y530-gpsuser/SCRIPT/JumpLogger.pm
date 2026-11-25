package JumpLogger;
use strict;
use warnings;
use Exporter 'import';

use lib $ENV{BPE};
use bpe_util;

our @EXPORT = qw(logJump jumpAndLog);

my $JUMP_LOG = "$ENV{HOME}/perl/JUMP.log";

# ---------------------------------------------------------------------------
sub logJump {
  my ($bpe, $target) = @_;

  eval {
    open(my $JL, '>>', $JUMP_LOG) or return;

    my $time   = scalar localtime();

    print $JL join(" | ",
      $time,
      "TARGET=$target",
    ), "\n";

    close($JL);
  };
}

# ---------------------------------------------------------------------------
sub jumpAndLog {
  my ($bpe, $target) = @_;
  logJump($bpe, $target);
  prtGoto($bpe, $target);
}

1;
