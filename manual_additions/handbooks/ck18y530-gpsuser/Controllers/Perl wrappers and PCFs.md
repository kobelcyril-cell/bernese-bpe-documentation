# Perl wrappers and PCFs

The wrappers in `~/perl/ZDGNSS` launch the PCFs listed below. Run a wrapper with `-h` for its available options. PCF names link to the generated PCF reference when that file is present in the selected GPSUSER. The interactive [[Controllers/ZDGNSS run package.md|run package]] bundles a set of stage wrappers in `pcs/`.

## Preparation and screening

- `preparation.pl` runs [[ZDGNSS_PREPARATION.PCF]].
- `preprocessing.pl` runs [[ZDGNSS_PREPROCESSING.PCF]].
- `codescreening.pl` runs [[ZDGNSS_CODESCREENING.PCF]].
- `phasescreening.pl` runs [[ZDGNSS_PHASESCREENING.PCF]].

## Solution stages

- `fa.pl` runs [[ZDGNSS_SOL_FA.PCF]].
- `ar.pl` runs [[ZDGNSS_AR.PCF]].
- `ia.pl` runs [[ZDGNSS_SOL_IA.PCF]].
- `finish.pl` runs [[ZDGNSS_FINISH.PCF]].
- `3d.pl` runs [[ZDGNSS_3D.PCF]].
- `ppp.pl` runs [[ZDGNSS_PPP.PCF]].

## Final processing and clock densification

- `ia_final.pl` runs [[ZDGNSS_SOL_FINAL.PCF]].
- `finish_final.pl` runs [[ZDGNSS_FINISH_FINAL.PCF]].
- `3d_final.pl` runs [[ZDGNSS_3D_FINAL.PCF]].
- `clkden.pl` runs [[ZDGNSS_CLKDEN.PCF]].
- `clkden_final.pl` runs [[ZDGNSS_CLKDEN_FINAL.PCF]].

The `ppp_manual.pl`, `ia_final_manual.pl`, `3d_final_manual.pl` and `clkden_manual.pl` variants select the same PCF as their corresponding wrapper. Check each wrapper's variables and defaults before treating the variants as interchangeable.

## Comparison and validation

- `cmpsol_code.pl` and `cmpsol_mgex.pl` are the CODE and MGEX comparison wrappers. Their help points to [[ZDGNSS_CMPSOL.PCF]].
- `val_rapid_1d.pl` and `val_rapid_3d.pl` launch [[ZDGNSS_VALSOL.PCF]] with settings for the rapid one-day and three-day solutions.

For the routine worker, scheduling and logs, see [[Operations_and_Tools/Scheduled ZDGNSS runs.md|Scheduled ZDGNSS runs]]. The spacecraft-specific launchers are documented separately in [[Controllers/LEO wrappers.md|LEO Perl wrappers]].

## Process a day relative to today

The wrappers support `-lw=R` with an offset `R`. The command below runs preparation for campaign `CK_ZDGNSS` for the day three days before the current day.

```bash
~/perl/preparation.pl -lw=R -camp=CK_ZDGNSS R=3
```
