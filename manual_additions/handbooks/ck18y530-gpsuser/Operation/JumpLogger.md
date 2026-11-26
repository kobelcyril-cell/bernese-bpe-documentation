This perl-module allows to check whether a jump in an BPE has been performed.
"JumpLogger.pm"
It is located in ck18y530/GPSUSER/SCRIPT.
If you want to use it:
Copy the JumpLogger.pm to your SCRIPT-directory.
Change the path in the "JumpLogger.pm" (line 11) to a location where you want to have to LOG-file. This LOG-file consists of the Jumps performed.
To use it in any SCRIPT:
import the module (in the very beginning after Header and after @ISA...)

use lib "$ENV{HOME}/GPSUSER/SCRIPT";
use JumpLogger qw(logJump);

And then before the prtGoto use the "logJump-command". For example:

logJump($bpe, $param2);
prtGoto(\$bpe,$param2) ;

You can also use the jumpAndLog-function, but this one has not been tested recently, so no guarantee that it's working.
