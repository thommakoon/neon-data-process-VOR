# VVOR
MATLAB/OCTAVE script for VVOR &amp; VORS extended analysis. 

WARNING: OCTAVE results has not been validated, and could be unaccuracy, specially for saccade analysis & PR score

## INSTALLATION & USE
Copy all files to your MATLAB - OCTAVE documents directory.
+ MATLAB (ver. 2015b): You will need signal toolbox. To run VVOR navigate to your VVOR folder and type `vvor`
+ OCTAVE (ver. 4.0.3): You will need signal package, type `pkg install -forge control` and `pkg install -forge signal`, each time you open OCTAVE you need to type `pkg load signal` (this should be not neccesary if you use a previous to 4.2 version if you used `pkg install -forge -auto signal` command to install signal package). To run VVOR navigate to your VVOR folder and type `vvor`

## SUPPORTED VVOR FILES
To use VVOR you need the exported .csv results file from ICS Impulse version 4.0 ® (Only English or Spanish location are supported). If there are more than one test results on the file only the last test will be loaded (you can delete other existing VVOR test from .csv file easily using a text editor)

### Disclosure
VVOR is an experimental software never use it with diagnostic purposes. 
The VVOR software is free and open source, see the source code for copying conditions and copyright terms.
There is ABSOLUTELY NO WARRANTY, not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

Thank you very much for your interest in our software, 
The authors.
