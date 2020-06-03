import DirectDmTargets as dddm
import wimprates as wr
import numpy as np
import argparse
assert wr.__version__ != '0.2.2'
import multiprocessing
import time
import os
import warnings


# # Direct detection of Dark matter using different target materials #
# 
# Author:
# 
# Joran Angevaare <j.angevaare@nikef.nl>
# 
# Date:
# 
# 7 november 2019 
# 
print("run_dddm_multinest.py::\tstart")
parser = argparse.ArgumentParser(description="Running a fit for a certain set of parameters")
parser.add_argument('-sampler', type=str, default = 'multinest', help="sampler (multinest or nestle)")
parser.add_argument('-mw', type=np.float, default=50., help="wimp mass")
parser.add_argument('-cross_section', type=np.float, default=-45, help="wimp cross-section")
parser.add_argument('-poisson', type=str, default='no', help="Add poisson noise to the test dataset")
parser.add_argument('-nlive', type=int, default=1024, help="live points used by multinest")
parser.add_argument('-tol', type=float, default=0.1, help="tolerance for opimization (see multinest option dlogz)")
parser.add_argument('-notes', type=str, default="default", help="notes on particular settings")
parser.add_argument('-bins', type=int, default=10, help="the number of energy bins")
parser.add_argument('-target', type=str, default='Xe', help="Target material of the detector (Xe/Ge/Ar)")
parser.add_argument('-nparams', type=int, default=2, help="Number of parameters to fit")
parser.add_argument('-priors_from', type=str, default="Pato_2010", help="Obtain priors from paper <priors_from>")
parser.add_argument('-verbose', type=float, default=0, help="Set to 0 (no print statements), 1 (some print statements) or >1 (a lot of print statements). Set the level of print statements while fitting.")
parser.add_argument('-shielding', type=str, default="default", help="yes / no / default, override internal determination if we need to take into account earth shielding.")
parser.add_argument('-save_intermediate', type=str, default="no", help="yes / no / default, override internal determination if we need to take into account earth shielding.")
parser.add_argument('-multicore_hash', type=str, default="", help="no / default, override internal determination if we need to take into account earth shielding.")

args = parser.parse_args()
yes_or_no = {"yes": True, "no": False}

if args.sampler == 'multinest':
    # MPI functionality only used for multinest
    try:
        from mpi4py import MPI
        rank = MPI.COMM_WORLD.Get_rank()
    except (ModuleNotFoundError, ImportError) as e:
        warnings.warn('Cannot run in multicore mode as mpi4py is not installed')
        rank = 0
    print(f"info\nn_cores: {multiprocessing.cpu_count()}\npid: {os.getpid()}\nppid: {os.getppid()}\nrank{rank}")
time.sleep(5)

print(f"run_dddm_multinest.py::\tstart for mw = {args.mw}, sigma = "
      f"{args.cross_section}. Fitting {args.nparams} parameters")
stats = dddm.NestedSamplerStatModel(args.target, args.verbose)
stats.sampler = args.sampler

if args.shielding != "default":
    stats.config['earth_shielding'] = yes_or_no[args.shielding.lower()]
    stats.set_models()
else:
    assert False
#TODO
stats.config['poisson'] = yes_or_no[args.poisson]
stats.config['notes'] = args.notes
stats.config['n_energy_bins'] = args.bins

stats.set_prior(args.priors_from)
stats.set_models()
stats.config['prior']['log_mass'] = {'range': [int(np.log10(args.mw)) - 2.5, int(np.log10(args.mw)) + 3.5], 'prior_type': 'flat'}
stats.config['prior']['log_cross_section'] = {'range': [int(args.cross_section) - 7, int(args.cross_section) + 5], 'prior_type': 'flat'}
stats.config['prior']['log_mass']['param'] = stats.config['prior']['log_mass']['range']
stats.config['prior']['log_cross_section']['param'] = stats.config['prior']['log_cross_section']['range']
stats.config['save_intermediate'] = yes_or_no[args.save_intermediate.lower()]
#TODO change to set_fit_parameters
stats.set_benchmark(mw=args.mw, sigma=args.cross_section)
stats.fit_parameters = stats.known_parameters[:args.nparams]
stats.eval_benchmark()
stats.nlive = args.nlive
# Save the number of live points in config to be sure
stats.config['nlive'] = args.nlive
stats.tol = args.tol
stats.print_before_run()

if args.multicore_hash != "":
    stats.get_save_dir(hash=args.multicore_hash)
    stats.get_tmp_dir(hash=args.multicore_hash)
if stats.sampler == 'multinest':
    stats.run_multinest()
elif stats.sampler == 'nestle':
    stats.run_nestle()
if args.multicore_hash == "" or (args.sampler == 'multinest' and rank == 0):
    stats.save_results()
assert stats.log_dict['did_run']


print(f"run_dddm_multinest.py::\tfinished for mw = {args.mw}, sigma = {args.cross_section}")
print("finished, bye bye")
