# ZDGNSS run package

`~/ZDGNSS_RUN` contains the files for preparing and launching an interactive ZDGNSS installation. For an existing scheduled run, see [[Operations_and_Tools/Scheduled ZDGNSS runs.md|Scheduled ZDGNSS runs]].

## Set up a run with the wizard

The wizard `zdgnss_wizard.py` guides you through choosing a destination for the run package, creating a campaign and copying the relevant PCFs. It can open the toolbox and the BPE launcher in the selected installation. In the launcher, choose the campaign and sessions, review the selected stages, then use **Dry Run** to check the generated commands. See [[Start/Run your first session.md|Quick start]] for the wizard command.

## Files used during a run

- `start_bpe_gui.py` is the interactive launcher. It reads and saves launcher settings in `bpe_config.json` beside the launcher.
- `pcs/` contains the stage wrappers. Each wrapper launches a PCF. Use the [[Controllers/Perl wrappers and PCFs.md|wrapper reference]] to select a stage.
- An actual launch writes and starts a detached `bpe_worker.py`. The wizard excludes the older worker when copying the installation. The generated worker records launcher messages and per-job output under the selected log location.
- `Tools/` contains the Qt toolbox. This copy includes **PCF File History**. See [[Operations_and_Tools/Toolbox and maintenance.md|Toolbox and maintenance]] for the two installed copies.

## Supporting code

- `perl/` contains `RetryHelper.pm` and `orb_ver.com`. See [[Operations_and_Tools/Monitoring and recovery.md|Monitoring and recovery]] for the retry helper.
- `python/` contains clock-completeness and station-list helpers. `python/validation_plot/` contains the COMPAR2 and ORB_VER plotters and their shared plotting code.
- `matlab/` contains GNSS station selection, clock and pole-file comparison, and component-statistics helpers.

The wrapper overview and the [[System_Overview/ZDGNSS PCF guide.md|PCF guide]] cover the next level below the launcher.
