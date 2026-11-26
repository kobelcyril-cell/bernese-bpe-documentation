# Perl wrappers and PCFs

Each wrapper launches the PCF listed below. Run the wrapper with `-h` for its available options. PCF names link to the generated PCF reference when that file is present in the selected GPSUSER.

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

## Process a day relative to today

The wrappers support `-lw=R` with an offset `R`. The command below runs preparation for campaign `CK_ZDGNSS` for the day three days before the current day.

```bash
~/perl/preparation.pl -lw=R -camp=CK_ZDGNSS R=3
```
