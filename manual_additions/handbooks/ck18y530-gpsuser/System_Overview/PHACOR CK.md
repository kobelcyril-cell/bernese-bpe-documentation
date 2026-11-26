# PHACOR phase correction

The project build in `~/PHACOR_CK` reads GPSEST narrow-lane bias (NLB) logs and estimates satellite clock and orbit corrections from zero-difference ambiguities. Its program name is `PHACOR` and the executable present on Sedna is `EXE_GNU/PHACOR`.

## Inputs and estimation

1. The executable reads its Bernese input file. Configure the GPSEST logs through `LOGFILES`. The program reads the constants file, station coordinates and orbit data for the geometry.
2. It builds an ambiguity grid, forms between-satellite observation intervals and clusters them. It can estimate jump parameters when configured to check phase jumps.
3. It solves a weighted system separately for each selected GNSS constellation. It uses datum and orbit constraints, then derives residuals, satellite quality statistics and corrections.

## Outputs and checks

When all selected systems solve successfully, the program writes corrected BIA, OSB, CLK and PRE orbit products to the `BIAFILE_MOD`, `OSBFILE_MOD`, `CLKFILE_MOD` and `ORBITFILE_MOD` destinations. It requires each of these output names to be set. The program report includes the inputs, processing trace and statistics. With debug enabled, `DEBUG_OUT` selects the detailed trace file.

Start with the report if a product is missing. The main program records conditions such as no selected NLB logs, a constellation with no usable observation intervals and a failed solution. These conditions help identify whether to inspect the input selection, the observations or the solve.

`FOR/PHACOR.f90` contains the processing driver. `FOR/D_PHACOR.f90` contains the supporting modules. `OBJ_GNU/Makefile` provides the GNU build configuration.
