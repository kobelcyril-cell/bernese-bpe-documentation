# Quick start

## Start the wizard

Run the following command from a terminal on the processing host.

```bash
python3 /storage/homefs/ck18y530/ZDGNSS_RUN/zdgnss_wizard.py &
```

Follow the prompts in the wizard. If you are preparing a new GPSUSER, see [[Start/Software and setup.md|Software and setup]] for the required processing components.

## Before starting a custom sequence

If you want to select or reorder individual processing jobs, open the [[Controllers/Python run controller.md|Python run controller]]. For a first run with that controller, use **Dry-Run** to review the generated commands, campaign and session selection before choosing **START BPE**.

## Follow the run

Use [[Operations_and_Tools/Monitoring and recovery.md|Monitoring and recovery]] to check job status and locate logs. See [[Operations_and_Tools/Quality checks and plots.md|Quality checks and plots]] when the run has produced its outputs.
