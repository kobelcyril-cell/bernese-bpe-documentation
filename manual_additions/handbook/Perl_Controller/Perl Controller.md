Every processing step may be started using a specific Perl-script:

[[preparation.pl]]
[[preprocessing.pl]]
[[codescreening.pl]]
[[phasescreening.pl]]
[[fa.pl]]
[[ar.pl]]
[[ia.pl]]
[[finish.pl]]
[[3d.pl]]
[[ppp.pl]]
[[ia_final.pl]]
[[finish_final.pl]]
[[3d_final.pl]]
[[clkden.pl]]


All perl controllers have the option to run them using the option "R"
e.g., 
~/perl/preparation.pl -lw=R -camp=CK_ZDGNSS R=3
which enables the processing of the current day - offset,
whereby the offset is set via R.
