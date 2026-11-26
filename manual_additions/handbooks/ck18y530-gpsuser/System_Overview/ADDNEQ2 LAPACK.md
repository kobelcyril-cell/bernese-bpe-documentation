# ADDNEQ2 with LAPACK

The project build in `~/ADDNEQ2_LAPACK` stacks Bernese normal equations (NEQs) and solves the combined system. The executable on Sedna is `EXE_IFC/ADDNEQ2`. The ZDGNSS three-day workflows have dedicated `ZD_ADDNEQ2_LA_P` and `ZD_ADDNEQ2_LA_E` jobs. The solution and finish workflows also have a LAPACK-related processing path. See the [[System_Overview/ZDGNSS PCF guide.md|PCF guide]] to locate these jobs.

## How it solves the system

`ADDNEQ2.f90` drives the stacking and calls the solver. `NEQSOLVE.f90` copies the normal matrix into full storage and uses LAPACK `DPOTRF` for Cholesky factorisation, `DPOTRS` for the solution vector and `DPOTRI` for the inverse. It copies the inverse back into the normal-equation representation for subsequent use. `PARELIMI.f90` is also part of the project build.

## Build and diagnose

- `FOR/compile_addneq2.sh` expects Intel `ifort` and the Bernese library and module directories. It links Intel MKL and the Bernese IFC library and writes `EXE_IFC/ADDNEQ2`.
- The source names under `FOR` are links into `FOR/BERN`. The top-level folder also contains source copies. Identify the source location used by the build script before comparing versions.
- `compile.txt` records older commands using an `ADDNEQ2_LAPACK2` path. Use the project build script as the reference for the current directory layout.
- In the program print file, check the `DPOTRF`, `DPOTRS` and `DPOTRI` return codes and the inversion timing. A zero LAPACK return code indicates success for that operation. If the solve fails, check the preceding NEQ assembly and datum checks in the corresponding PCF.
