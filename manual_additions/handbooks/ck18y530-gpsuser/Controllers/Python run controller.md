# Python run controller

The controller `start_bpe_gui.py` is available in `/storage/homefs/ck18y530/perl/ZDGNSS`. It starts the selected [[Controllers/Perl wrappers and PCFs.md|Perl wrappers]] in the order shown in the job list.

## Configure a run

1. Choose the campaign and partition.
2. Set the first session and the number of sessions.
3. Add the required jobs and use the up and down controls to set their order.
4. Give the output log a name if you want to keep a run log. Use the wait condition when the launch of jobs must be spaced out.
5. Choose **Dry-Run** to display the commands. Review them before choosing **START BPE**.

## Run a single stage

Use the matching Perl wrapper directly when you only need one step. Its `-h` option gives the arguments for that wrapper.
