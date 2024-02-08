import pickle
import time
import traceback

import numpy
import torch
import tqdm

import src.flink.flink_config_space
from src.optimizer.base_optimizer import BaseAbstractOptimizer
from src.HistoryContainer.mtbo_history_container import MTBOHistoryContainer
from ConfigSpace import ConfigurationSpace, Configuration
from botorch.fit import fit_gpytorch_mll
from gpytorch.mlls import ExactMarginalLogLikelihood
import gpytorch

DEVICE = torch.device("cpu")


class MTBOOptimizer(BaseAbstractOptimizer):
    def __init__(self,
                 objective_function: callable,
                 max_run: int,
                 initial_samples: int,
                 config_space: ConfigurationSpace,
                 similar_factor: float,  # 0-1, a threshold for judging similar jobs.
                 task_description,
                 num_constraints: int,
                 tps_constraints: list,
                 acqf_opt_restarts=12,
                 acqf_opt_raw_samples=64,
                 constraints_dropout=False,
                 use_worst_approximation=False,
                 filter_gaussian_scale=0.5,
                 filter_dist_threshold=0.2,
                 auto_filter=False,
                 tmp_dump=True
                 ):
        super().__init__()

        self.filter_gaussian_scale = filter_gaussian_scale
        self.filter_dist_threshold = filter_dist_threshold
        self.auto_filter = auto_filter
        self.similar_factor = similar_factor
        self.constraints_dropout = constraints_dropout
        self.num_constraints = num_constraints
        self.objective_function = objective_function
        self.max_run = max_run
        self.task_description = task_description
        self.config_space = config_space
        self.initial_samples = initial_samples
        self.iter_count = 0
        self.total_dimension = len(config_space.get_hyperparameters())
        self.history_container = MTBOHistoryContainer(task_description=self.task_description)
        self.tps_constraints = tps_constraints
        self.acqf_opt_restarts = acqf_opt_restarts
        self.acqf_opt_raw_samples = acqf_opt_raw_samples
        self.use_worst_approximation = use_worst_approximation
        self.tmp_dump = tmp_dump

        # Steps for each iteration:
        # 1. Obtain train_x, train_y from history_container.
        # 2. Identify redundant constraints based on the manually defined threshold.
        # 3. Compress redundant constraints and generate new compressed_train_y.
        # 4. Model the objective and compressed constraint functions (all in compressed_train_y) using Multi-Task GP.
        # 5. Select a new candidate using the Constrained EI acquisition function.

    def observe(self, config: Configuration):
        try:
            if config in self.history_container.data.keys():
                print("Repeat Config Detected")
                config = self.repeat_config_strategy(config)

            self.iter_count += 1
            result = self.objective_function(config)
            self.history_container.add(config, result)
        except Exception as e:
            print("Failed when observing config:", config)
            print(e)

    def repeat_config_strategy(self, config: Configuration):
        print("Using repeat config strategy: random")
        return self.config_space.sample_configuration()

    def get_CEI_candidate(self):

        # Obtain the MTGP model, and the number of compressed constraints.
        gp, num_constraints, best_f = self.build_multi_task_model()

        # each constraint will be normalized based on the throughput threshold. Values greater than 1 are feasible.
        CEI_constraints = dict()
        for i in range(num_constraints):
            CEI_constraints[i + 1] = (1, None)

        # Initialize the acquisition function.
        from botorch.models import ModelListGP
        gp = ModelListGP(gp)
        from botorch.acquisition.analytic import ConstrainedExpectedImprovement
        ConstrainedEI = ConstrainedExpectedImprovement(
            model=gp,
            best_f=best_f,
            objective_index=0,
            constraints=CEI_constraints,
            maximize=False
        )

        # Optimize the acquisition function to select a new candidate.
        from botorch.optim import optimize_acqf
        bounds = torch.stack([torch.zeros(self.total_dimension, dtype=torch.float64),
                              torch.ones(self.total_dimension, dtype=torch.float64)])
        candidate, acq_value = optimize_acqf(
            ConstrainedEI, bounds=bounds.to(DEVICE), q=1,
            num_restarts=self.acqf_opt_restarts,
            raw_samples=self.acqf_opt_raw_samples
        )
        return candidate

    def build_multi_task_model(self):

        # Obtain train_x and train_y from history_container
        train_x = self.history_container.get_train_x().to(DEVICE)

        train_obj = self.history_container.get_train_obj()
        train_obj = torch.unsqueeze(train_obj, dim=1)  # convert row vector to column vector

        # scaling the input objective function to zero mean and unit variance.
        train_obj = (train_obj - train_obj.mean()) / train_obj.std()

        # TODO: There is an issue here - when the number of original constraints is 1, it is a row vector;
        # when there are multiple constraints, it's a 2-D matrix. In our case, we only use multiple constraints,
        # so no need to handle this for now.
        full_train_constraints = self.history_container.get_train_constraints()

        # Normalize all constraint values separately based on throughput threshold.
        for j in range(self.num_constraints):
            full_train_constraints[:, j] = (full_train_constraints[:, j] - 0) / (self.tps_constraints[j] - 0)
        normalized_constraints = full_train_constraints

        # Additional smoothing operations can be applied to handle extremely noisy observations.
        if self.auto_filter:
            filtered_constraints = self.do_best_gpr_filter(train_x, normalized_constraints)
        else:
            filtered_constraints = self.do_gaussian_filter(train_x, normalized_constraints)

        # Identify redundant constraints using manually defined similarity thresholds
        if self.constraints_dropout:
            compressed_train_constraints = self.get_compressed_constraints(filtered_constraints)
        else:
            compressed_train_constraints = filtered_constraints

        # Concatenate train_obj and compressed_train_constarints to obtain a complete train_y
        train_y = torch.cat((train_obj, compressed_train_constraints), dim=1).to(DEVICE)

        # If there are feasible observations, take the minimum objective value as min_f
        # If no constraints are met, assign a large integer, to guide CEI search in the feasible region.
        feasible_y = []
        for i in range(compressed_train_constraints.shape[0]):
            feasible = True
            for j in range(compressed_train_constraints.shape[1]):
                if compressed_train_constraints[i, j] < 1:
                    feasible = False
            if feasible:
                feasible_y.append(train_obj[i, 0])
        if len(feasible_y) < 1:
            min_f = 65545
        else:
            min_f = min(feasible_y)

        # Learn GP model's hyperparameters
        from botorch.models import KroneckerMultiTaskGP
        gp = KroneckerMultiTaskGP(train_x, train_y).to(DEVICE)

        mll = ExactMarginalLogLikelihood(gp.likelihood, gp).to(DEVICE)
        gp.train()
        gp.likelihood.train()
        output = gp(train_x)
        loss = -mll(output, train_y)
        print('MTGP initial_train_loss=', loss)
        from botorch.fit import fit_gpytorch_mll_torch
        fit_gpytorch_mll(mll, optimizer=fit_gpytorch_mll_torch, optimizer_kwargs={'step_limit': 500})
        # fit_gpytorch_mll(mll, optimizer_kwargs={'timeout_sec': 20})
        print('Iter %d/%d - Loss: %.3f   noise: %.3f' % (
            50, 50, loss.item(),
            gp.likelihood.noise.item()
        ))
        output = gp(train_x)
        loss = -mll(output, train_y)
        print('MTGP final_train_loss=', loss)

        gp.eval()
        gp.likelihood.eval()
        return gp, compressed_train_constraints.shape[1], min_f

    def get_candidate_config(self, candidate_array):
        return Configuration(configuration_space=self.config_space, vector=candidate_array.cpu())

    def calculate_similarity(self):
        pass

    def get_compressed_constraints(self, full_train_constraints):
        dist_threshold = self.similar_factor * (self.iter_count ** 0.5)

        from scipy.cluster.vq import kmeans

        constraints = torch.t(full_train_constraints)

        for k in range(self.num_constraints - 1):
            codebook, distortion = kmeans(constraints, k + 1)
            cluster_centroids = torch.t(torch.tensor(codebook, dtype=torch.float64))

            if self.judge_similarity_threshold(full_train_constraints, cluster_centroids,
                                               dist_threshold):  # 判断聚类是否满足threshold要求
                if self.use_worst_approximation:
                    worst_constraints = self.get_conservative_prototype(k + 1, cluster_centroids,
                                                                        full_train_constraints)
                    return worst_constraints
                else:
                    return cluster_centroids  # Note: The order of centroids returned is unstable. However, it does not impact the tuning process.

        return full_train_constraints

    def judge_similarity_threshold(self, full_train_constraints, cluster_centroids, dist_threshold):
        # check it the inter-cluster distance is smaller than the manually defined threshold.
        for i in range(full_train_constraints.shape[1]):
            success_flag = 0
            for j in range(cluster_centroids.shape[1]):
                if torch.pairwise_distance(full_train_constraints[:, i], cluster_centroids[:, j]) < dist_threshold:
                    success_flag += 1
            if success_flag < 1:
                return False
        return True

    def get_conservative_prototype(self, k, cluster_centroids, full_constraints):
        # Find the cluster each constraint belongs based on the k cluster centroids.
        # Within each cluster, the final prototype is the worst value among all observations.

        clusters = []
        for _ in range(k):
            clusters.append([])

        for i in range(full_constraints.shape[1]):
            full_constraint = full_constraints[:, i]
            nearest = -1
            dist = 10000
            for j in range(k):
                centroid = cluster_centroids[:, j]
                tmp_dist = torch.pairwise_distance(full_constraint, centroid)
                if tmp_dist < dist:
                    nearest = j
                    dist = tmp_dist
            clusters[nearest].append(full_constraint)

        res = []
        for cluster in clusters:
            worst_constraint = cluster[0].clone()
            for i in range(len(cluster)):
                for j in range(full_constraints.shape[0]):
                    if worst_constraint[j] > cluster[i][j]:
                        worst_constraint[j] = cluster[i][j]
            worst_constraint = worst_constraint.tolist()
            res.append(worst_constraint)

        res = torch.t(torch.tensor(res, dtype=torch.float64))
        return res

    def get_different_train_y(self):
        pass

    def do_gaussian_filter(self, x, constraints: torch.Tensor):
        # An additional Gaussian Filter, which can be applied to deal with extreme noisy observations
        threshold = self.filter_dist_threshold
        dist_treshold = threshold * self.total_dimension ** 0.5
        from torch.distributions import Normal
        normal = Normal(loc=0, scale=self.filter_gaussian_scale)
        filtered_constraints = torch.zeros(size=constraints.shape, dtype=torch.float64)

        weight_sums = torch.zeros(x.shape[0])

        for observation in range(x.shape[0]):
            for neighbors in range(x.shape[0]):

                dist = torch.pairwise_distance(x[observation], x[neighbors])

                if dist < dist_treshold + 1E-3:
                    w = normal.log_prob(dist).exp()
                    filtered_constraints[observation] += w * constraints[neighbors]
                    weight_sums[observation] += w
            filtered_constraints[observation] = filtered_constraints[observation] / weight_sums[observation]

        return filtered_constraints

    def do_best_gpr_filter(self, x, constraints: torch.Tensor):
        # An additional GPR smoothing with learned noise level.
        print("Start to train GPR")
        filtered = []
        for idx in range(constraints.shape[1]):
            single_constraint = constraints[:, idx]

            # initialize likelihood and model
            likelihood = gpytorch.likelihoods.GaussianLikelihood()
            model = RBFExactGPModel(x, single_constraint, likelihood)

            training_iter = 50

            # Find optimal model hyperparameters
            model.train()
            likelihood.train()

            optimizer = torch.optim.Adam(model.parameters(), lr=0.1)  # Includes GaussianLikelihood parameters
            mll = gpytorch.mlls.ExactMarginalLogLikelihood(likelihood, model)

            for i in range(training_iter):
                optimizer.zero_grad()
                output = model(x)
                loss = -mll(output, single_constraint)
                loss.backward()
                optimizer.step()

            model.eval()
            likelihood.eval()
            with torch.no_grad(), gpytorch.settings.fast_pred_var():
                observed_pred = likelihood(model(x))
            filtered.append(observed_pred.mean.numpy())
        filtered = torch.t(torch.tensor(numpy.array(filtered)))
        return filtered

    def run(self):
        # initial sampling
        self.observe(self.config_space.get_default_configuration())
        for i in range(self.initial_samples - 1):
            self.observe(self.config_space.sample_configuration())

        # iter run
        for i in tqdm.tqdm(range(self.max_run - self.initial_samples)):
            if self.tmp_dump:
                # dump tmp history in case of unexpected termination
                f = open('history/tmp', 'wb')
                pickle.dump(self.history_container, f, 0)
                f.close()

            while True:
                try:
                    candidate_array = self.get_CEI_candidate()[0]
                    break
                except NotImplementedError as e:
                    print("NotImplementedError")
                    info = traceback.format_exc()
                    print(info)
                    return
                except Exception as e:
                    print("An exception occurs during BO, try again.")
                    info = traceback.format_exc()
                    print(info)
            candidate_config = self.get_candidate_config(candidate_array)
            self.observe(candidate_config)

        print("The Best Config is:", self.history_container.get_best_config())
        print("The Best Performance is: ", self.history_container.get_best_perf())
        # return

        return self.history_container

    def get_history(self):
        return self.history_container


# A simple GP model with Matern kernel for GPR smoothing. It is not used in our experiments.
class RBFExactGPModel(gpytorch.models.ExactGP):
    def __init__(self, train_x, train_y, likelihood):
        super(RBFExactGPModel, self).__init__(train_x, train_y, likelihood)
        self.mean_module = gpytorch.means.ConstantMean()
        self.covar_module = gpytorch.kernels.ScaleKernel(gpytorch.kernels.MaternKernel())

    def forward(self, x):
        mean_x = self.mean_module(x)
        covar_x = self.covar_module(x)
        return gpytorch.distributions.MultivariateNormal(mean_x, covar_x)


if __name__ == "__main__":

    from openbox import sp
    from src.util.hartmann3 import hartmann3_w_AGN


    def objective(config: Configuration):
        params = config.get_dictionary()
        constraint = 5 + hartmann3_w_AGN([params['x_1'], params['x_2'], params['x_3']], 1)
        return [hartmann3_w_AGN([params['x_1'], params['x_2'], params['x_3']], 0),
                -hartmann3_w_AGN([params['x_1'], params['x_2'], params['x_3']], 1),
                constraint,
                constraint,
                constraint]


    from src.flink.flink_config_space import get_flink_1_13_6_config_space

    space = sp.Space()
    # space = get_flink_1_13_6_config_space()
    x_1 = sp.Real("x_1", 0, 1, default_value=0)
    x_2 = sp.Real("x_2", 0, 1, default_value=0)
    x_3 = sp.Real("x_3", 0, 1, default_value=1)
    space.add_variables([x_1, x_2, x_3])
    tt = MTBOOptimizer(
        similar_factor=0.2,
        objective_function=objective,
        max_run=50,
        initial_samples=5,
        config_space=space,
        task_description="test",
        num_constraints=4,
        tps_constraints=[1, 1, 1, 1],
        acqf_opt_restarts=4,
        acqf_opt_raw_samples=8,
        constraints_dropout=True,
        use_worst_approximation=True,
        filter_gaussian_scale=1,
        filter_dist_threshold=0.2,
        auto_filter=True
    )

    st = time.time()
    history = tt.run()
    ed = time.time()
    print("Time is", ed - st)
    print('Best is', history.get_best_perf())
