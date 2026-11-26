Start [[Perl Controller]]s in defined sequence

The tool can be found in /storage/homefs/ck18y530/perl/ZDGNSS
- **==start_bpe_gui.py==**
This tools allows to start perl-scripts in a dedicated sequence. The order can be changed by moving the jobs up or down. The available [[Perl Controller]] start parts of the full processing chain. 

Following the Bernese-style, one can choose the campaign (and partition), the first session and the number of sessions. To generate a LOG for the BPE run, it is possible to specify name for the output file. The wait-condition may be used to enforce a waiting between the starting of the scripts. The function "Dry-Run" simply shows the commands which would be executed. When using this tool for the first time, it is recommended to try the "Dry-Run" first (before "START BPE").
