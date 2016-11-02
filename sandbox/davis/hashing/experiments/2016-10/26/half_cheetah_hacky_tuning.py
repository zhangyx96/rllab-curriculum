from __future__ import print_function
from __future__ import absolute_import

info = """Trying several different hacky hashes for sparse half cheetah"""

from rllab.misc.instrument import stub, run_experiment_lite
from sandbox.davis.hashing.algos.bonus_trpo import BonusTRPO
from sandbox.davis.hashing.bonus_evaluators.half_cheetah_hacky_hash import HalfCheetahHackyHash
from sandbox.rein.envs.half_cheetah_env_x import HalfCheetahEnvX
from sandbox.rocky.tf.baselines.linear_feature_baseline import LinearFeatureBaseline
from sandbox.rocky.tf.policies.gaussian_mlp_policy import GaussianMLPPolicy
from sandbox.rocky.tf.envs.base import TfEnv
import sandbox.davis.hashing.bonus_evaluators.half_cheetah_hacky_hash as hchh

import sys
import argparse

stub(globals())

from rllab.misc.instrument import VariantGenerator

N_ITR = 1000
N_ITR_DEBUG = 5

envs = [HalfCheetahEnvX()]

X = hchh.X
Z = hchh.Z
Y_angle = hchh.Y_angle
X_vel = hchh.X_vel
Z_vel = hchh.Z_vel
Y_ang_vel = hchh.Y_ang_vel


def experiment_variant_generator():
    vg = VariantGenerator()
    vg.add("env", map(TfEnv, envs))
    vg.add("batch_size", [5000], hide=True)
    vg.add("step_size", [0.01], hide=True)
    vg.add("max_path_length", [500], hide=True)
    vg.add("discount", [0.99], hide=True)
    vg.add("seed", range(5), hide=True)
    vg.add("bonus_coeff", [0.01])
    vg.add("indices", [[X, Z],
                       [X, Z, Y_angle],
                       [X, Z, X_vel, Z_vel],
                       [X, Z, Y_angle, X_vel, Z_vel, Y_ang_vel],
                       [X, Y_angle],
                       [X, Y_angle, X_vel, Y_ang_vel]])
    vg.add("dim_key", [16, 32, 64])
    vg.add("bonus_evaluator",
           lambda env, indices, dim_key: [HalfCheetahHackyHash(env.spec,
                                                               indices=indices,
                                                               dim_key=dim_key)],
           hide=True)
    return vg


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--local",
                        help="run experiment locally",
                        action="store_true")
    parser.add_argument("-v", "--visualize",
                        help="visualize simulations during experiment",
                        action="store_true")
    parser.add_argument("-d", "--debug",
                        help="run in debug mode (only one configuration; don't terminate machines)",
                        action="store_true")
    parser.add_argument("-i", "--info",
                        help="display experiment info (without running experiment)",
                        action="store_true")
    parser.add_argument("-n", "--n-itr", type=int,
                        help="number of iterations (overrides default; mainly for debugging)")
    parser.add_argument("-s", "--start-exp", type=int, default=0,
                        help="experiment number to start with (default 0)")
    args = parser.parse_args()
    if args.info:
        print(info.replace('\n', ' '))
        sys.exit(0)
    return args

if __name__ == '__main__':
    args = parse_args()
    exp_prefix = __file__.split('/')[-1][:-3].replace('_', '-')
    if args.debug:
        exp_prefix += '-DEBUG'
    N_ITR = args.n_itr if args.n_itr is not None else N_ITR_DEBUG if args.debug else N_ITR
    vg = experiment_variant_generator()
    variants = vg.variants()
    print("Running experiment {}.".format(exp_prefix))
    print("Number of experiments to run: {}.".format(len(variants) if not args.debug else 1))
    exp_number = 0
    for variant in variants:
        exp_number += 1
        if exp_number <= args.start_exp:
            continue
        exp_name = vg.to_name_suffix(variant)
        if exp_name == '':
            exp_name = None

        policy = GaussianMLPPolicy(
            name="policy",
            env_spec=variant["env"].spec,
            hidden_sizes=(64, 32),
        )

        baseline = LinearFeatureBaseline(variant["env"].spec)

        algo = BonusTRPO(
            bonus_evaluator=variant["bonus_evaluator"],
            bonus_coeff=variant["bonus_coeff"],
            env=variant["env"],
            policy=policy,
            baseline=baseline,
            batch_size=variant["batch_size"],
            whole_paths=True,
            max_path_length=variant["max_path_length"],
            n_itr=N_ITR,
            discount=variant["discount"],
            step_size=variant["step_size"],
            plot=args.visualize and args.local,
        )

        run_experiment_lite(
            algo.train(),
            n_parallel=1,
            snapshot_mode="last",
            seed=variant["seed"],
            plot=args.visualize and args.local,
            mode="local" if args.local else "ec2",
            exp_prefix=exp_prefix,
            terminate_machine=not args.debug
        )

        if args.debug:
            break  # Only run first experiment variant in debug mode
