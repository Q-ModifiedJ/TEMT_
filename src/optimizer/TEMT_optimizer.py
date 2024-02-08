import random

from gpytorch import ExactMarginalLogLikelihood
import tqdm
import traceback
import pickle

from src.optimizer.DCBO_optimizer import DCBOOptimizer
import torch
from botorch.fit import fit_gpytorch_mll

from scipy import stats
import numpy as np
from sklearn.decomposition import KernelPCA, PCA

DEVICE = torch.device("cpu")


class TEMTOptimizer(DCBOOptimizer):
    def __init__(self,
                 reserved_random_dimensions,
                 reserve_strategy="Spearman",
                 reserve_spearman_factor=0.2,
                 extraction_strategy="PCA",
                 extraction_important_strategy="most",
                 extraction_important_num_strategy="Spearman",
                 extraction_important_num=0.8,
                 fillingin_strategy_factor=0.5,
                 *args,
                 **kwargs):
        """

        :param reserved_random_dimensions:
            The number of parameters to be reserved when filtering out parameters, only effective for "Random" reserve strategy.
        :param reserve_strategy:
            Random, Spearman
        :param reserve_spearman_factor:
            a Spearman Correlation Coefficient (SCC) threshold. Configuration parameters with SCC less than the threshold will be dropped out. Only effective for "Spearman" reserve strategy.
        :param extraction_strategy:
            the strategy to further extract parameters, including "PCA", "Important", "Hierarchical"
        :param extraction_important_strategy:
            The strategy when using "Important" extraction strategy
            "most": retain parameters with the highest correlation; "sample": sample parameters based on correlation weights.
        :param extraction_important_num_strategy:
            The strategy of the number of extracted parameters.
                Spearman：based on Spearman Correlation Coefficient.
                Fixed：a manually defined number.
        :param extraction_important_num:
            Union[int, float]
            This parameter represents the number/threshold of parameters to be identified as direct parameters.:

            For Spearman extraction_important_num_strategy, it represents the threshold;
            For Fixed extraction_important_num_strategy, it represents the number of parameters."
        :param fillingin_strategy_factor:
            the ratio of using filling-random / filling-copy strategy when filling the dropped parameters.
        :param args:
        :param kwargs:
        """
        super(TEMTOptimizer, self).__init__(*args, **kwargs)

        # check params
        assert reserve_strategy in ["Random", "Spearman"]
        assert extraction_strategy in ["PCA", "Important", "Hierarchical"]
        assert extraction_important_strategy in ["most", "sample"]
        assert extraction_important_num_strategy in ["Spearman", "Fixed"]

        self.reserved_random_dimensions = reserved_random_dimensions
        self.reserve_strategy = reserve_strategy
        self.reserve_spearman_factor = reserve_spearman_factor
        self.extraction_strategy = extraction_strategy
        self.extraction_important_strategy = extraction_important_strategy
        self.extraction_important_num_strategy = extraction_important_num_strategy
        self.extraction_important_num = extraction_important_num
        self.fillingin_strategy_factor = fillingin_strategy_factor
        self.pca = None

        # Steps for each iteration:
        # 1. Obtain train_x, train_y from history_container.
        # 2. Identify redundant constraints based on the manually defined threshold.
        # 3. Compress redundant constraints and generate new compressed_train_y.
        # 4. Extract parameters for BO search from original configuration parameters.
        # 5. Model the objective and compressed constraint functions (all in compressed_train_y) using Multi-Task GP.
        # 6. Select a new candidate using the Constrained EI acquisition function.
        # 7. Reconstruct original configuration parameters from the candidate.

    def get_CEI_candidate(self):
        # Obtain the MTGP model, and the number of compressed constraints, the BO search space.
        gp, num_constraints, best_f, x_min, x_max, reserve_mask, extraction_decompose_mask, extraction_important_mask = self.build_multi_task_model()
        '''
        CEI constrained acquisition function with dynamic number of constraints.
        '''
        CEI_constraints = dict()
        for i in range(num_constraints):
            CEI_constraints[i + 1] = (1, None)

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

        # select a candidate
        from botorch.optim import optimize_acqf

        bounds = torch.stack([x_min,
                              x_max])

        candidate, acq_value = optimize_acqf(
            ConstrainedEI, bounds=bounds.to(DEVICE), q=1,
            num_restarts=self.acqf_opt_restarts,
            raw_samples=self.acqf_opt_raw_samples
        )

        # reconstruct original configuration parameters from the candidate

        if self.extraction_strategy == "PCA":
            # PCA reverse transform
            reserved_candidate = self.pca.inverse_transform(candidate) + 0.5
            reserved_candidate = reserved_candidate[0]
        elif self.extraction_strategy == "Important":
            # Filling-in strategy
            reserved_candidate = self.filling_in(candidate, reserve_mask=extraction_important_mask)
            reserved_candidate = np.array(reserved_candidate)
        elif self.extraction_strategy == "Hierarchical":
            # PCA reverse transform & Filling-in strategy
            candidate = candidate[0]
            total_candidate = torch.zeros(len(reserve_mask), dtype=torch.float64)

            for i in range(len(extraction_important_mask)):
                total_candidate[extraction_important_mask[i]] = candidate[i]

            to_inverse_candidate = torch.zeros(len(candidate) - len(extraction_important_mask),
                                               dtype=torch.float64).reshape(1, -1)

            if len(extraction_decompose_mask) != 0:
                for i in range(len(to_inverse_candidate)):
                    to_inverse_candidate[i] = candidate[i + len(extraction_important_mask)]

                inverse_transformed_candidate = self.pca.inverse_transform(to_inverse_candidate).reshape(-1) + 0.5

                for i in range(len(extraction_decompose_mask)):
                    total_candidate[extraction_decompose_mask[i]] = inverse_transformed_candidate[i]

            reserved_candidate = np.array(total_candidate)
        else:
            raise NotImplementedError

        # reserve_train_x -> full_candidate_x
        total_candidate = self.filling_in(torch.from_numpy(reserved_candidate), reserve_mask=reserve_mask)

        return total_candidate

    def filling_in(self, candidate_to_fill, reserve_mask):
        if random.random() < self.fillingin_strategy_factor:
            # filling-copy
            best_config_array = self.history_container.get_best_config().get_array()
            total_candidate = torch.tensor(best_config_array, dtype=torch.float64)
        else:
            # filling-random
            total_candidate = torch.rand(self.total_dimension, dtype=torch.float64)

        total_candidate[reserve_mask] = candidate_to_fill

        return total_candidate

    def get_reserve_mask(self, different_train_y):
        if self.reserve_strategy == "Random":
            total_dimension_index = list(range(self.total_dimension))
            reserve_mask = random.sample(total_dimension_index, self.reserved_random_dimensions)
        elif self.reserve_strategy == "Spearman":
            reserve_mask = []

            # Filter out parameters that are not correlated with any of the objective and constraint functions.
            train_X = self.history_container.get_train_x()
            for i in range(self.total_dimension):
                max_r = 0
                for j in range(different_train_y.shape[1]):
                    r, p = stats.spearmanr(train_X[:, i], different_train_y[:, j])
                    if abs(r) > max_r:
                        max_r = abs(r)
                if max_r >= self.reserve_spearman_factor:
                    reserve_mask.append(i)

            if len(reserve_mask) == 0:
                total_dimension_index = list(range(self.total_dimension))
                reserve_mask = random.sample(total_dimension_index,
                                             min(self.total_dimension, self.reserved_random_dimensions)
                                             )
        else:
            total_dimension_index = list(range(self.total_dimension))
            reserve_mask = total_dimension_index
        return sorted(reserve_mask)

    def get_important_mask(self, reserved_train_x, different_train_y):
        extraction_important_mask = []

        r_lst = []
        for i in range(reserved_train_x.shape[1]):
            r = 0
            for j in range(different_train_y.shape[1]):
                tmp_r, tmp_p = stats.spearmanr(reserved_train_x[:, i], different_train_y[:, j])
                r += abs(tmp_r)
            r = r / different_train_y.shape[1]
            r_lst.append(r)

        """
        Determine the number of important parameters.
        """

        num = 0
        if self.extraction_important_num_strategy == "Spearman":
            for r in r_lst:
                if r > self.extraction_important_num:
                    num += 1
        elif self.extraction_important_num_strategy == "Fixed":
            # If the remaining parameters are fewer than the predefined number of important parameters, fetch all the remaining parameters.
            num = min(self.extraction_important_num, reserved_train_x.shape[1])

        if self.extraction_important_strategy == "most":
            for r in sorted(r_lst, reverse=True):  # 降序排列，大的在前
                if len(extraction_important_mask) < num:
                    extraction_important_mask.append(r_lst.index(r))

        elif self.extraction_important_strategy == "sample":
            raise NotImplementedError

        else:
            extraction_important_mask = []

        return sorted(extraction_important_mask)

    def get_decomposed_train_x(self, reserved_train_x):
        reserved_train_x -= 0.5  # As configuration space belongs to [0,1], this transform them to 0-mean

        pca = KernelPCA(n_components=None, kernel='rbf', gamma=None, degree=3, kernel_params=None,
                        alpha=0.1, fit_inverse_transform=True, eigen_solver='auto', tol=0, max_iter=None,
                        remove_zero_eig=False,
                        random_state=None, copy_X=True, n_jobs=-1)
        decomposed_train_x = pca.fit_transform(X=reserved_train_x)
        contributions = pca.eigenvalues_ / sum(pca.eigenvalues_)
        cum_contribution = np.cumsum(contributions)

        decomposed_dimensions = max(np.where(cum_contribution > 0.8)[0][0], 1)

        self.pca = KernelPCA(n_components=decomposed_dimensions, kernel='rbf', gamma=None,
                             degree=3,
                             kernel_params=None,
                             alpha=0.1, fit_inverse_transform=True, eigen_solver='auto', tol=0, max_iter=None,
                             remove_zero_eig=False,
                             random_state=None, copy_X=True, n_jobs=-1)
        decomposed_train_x = self.pca.fit_transform(X=reserved_train_x)
        x_min = []
        x_max = []
        for i in range(decomposed_dimensions):
            x_min.append(np.min(decomposed_train_x[:, i]))
            x_max.append(np.max(decomposed_train_x[:, i]))

        return decomposed_train_x, x_min, x_max

    def build_multi_task_model(self):


        train_x = self.history_container.get_train_x().to(DEVICE)

        train_obj = self.history_container.get_train_obj()
        train_obj = torch.unsqueeze(train_obj, dim=1)
        # scaling the input to zero mean and unit variance.
        train_obj = (train_obj - train_obj.mean()) / train_obj.std()

        full_train_constraints = self.history_container.get_train_constraints()

        for j in range(self.num_constraints):
            full_train_constraints[:, j] = (full_train_constraints[:, j] - 0) / (self.tps_constraints[j] - 0)
        normalized_constraints = full_train_constraints

        if self.auto_filter:
            filtered_constraints = self.do_best_gpr_filter(train_x, normalized_constraints)
        else:
            filtered_constraints = self.do_gaussian_filter(train_x, normalized_constraints)

        if self.constraints_dropout:
            different_train_constraints = self.get_compressed_constraints(filtered_constraints)
        else:
            different_train_constraints = filtered_constraints

        train_y = torch.cat((train_obj, different_train_constraints), dim=1).to(DEVICE)

        feasible_y = []
        for i in range(different_train_constraints.shape[0]):
            feasible = True
            for j in range(different_train_constraints.shape[1]):
                if different_train_constraints[i, j] < 1:
                    feasible = False
            if feasible:
                feasible_y.append(train_obj[i, 0])

        if len(feasible_y) < 1:
            min_f = 65545
        else:
            min_f = min(feasible_y)

        """
        Hierarchical Parameter Selection
        """

        """
        Filter out irrelevant parameters.
        """
        reserve_mask = self.get_reserve_mask(train_y)
        reserved_train_x = train_x[:, reserve_mask]

        """
        Further extract parameters with direct input dimensions.
        """
        decomposed_train_x, x_min, x_max, extraction_decompose_mask, extraction_important_mask \
            = self.train_x_extraction(reserved_train_x=reserved_train_x, different_train_y=train_y)

        """
        build multi-task GP

        """
        from botorch.models import KroneckerMultiTaskGP
        decomposed_train_x = torch.from_numpy(decomposed_train_x)
        gp = KroneckerMultiTaskGP(decomposed_train_x, train_y).to(DEVICE)

        mll = ExactMarginalLogLikelihood(gp.likelihood, gp).to(DEVICE)
        output = gp(decomposed_train_x)
        loss = -mll(output, train_y)
        print('MTGP initial_train_loss=', loss)

        from botorch.fit import fit_gpytorch_mll_torch
        fit_gpytorch_mll(mll, optimizer=fit_gpytorch_mll_torch, optimizer_kwargs={'step_limit': 500})
        # fit_gpytorch_mll(mll, optimizer_kwargs={'timeout_sec': 10})
        gp.train()
        gp.likelihood.train()
        print('Iter %d/%d - Loss: %.3f   noise: %.3f' % (
            50, 50, loss.item(),
            gp.likelihood.noise.item()
        ))
        output = gp(decomposed_train_x)
        loss = -mll(output, train_y)
        print('MTGP final_train_loss=', loss)

        gp.eval()
        gp.likelihood.eval()
        return gp, different_train_constraints.shape[1], min_f, torch.tensor(x_min), torch.tensor(
            x_max), reserve_mask, extraction_decompose_mask, extraction_important_mask

    def train_x_extraction(self, reserved_train_x, different_train_y):
        total_reserved_dimension_index = list(range(reserved_train_x.shape[1]))
        if self.extraction_strategy == "PCA":
            decomposed_train_x, x_min, x_max = self.get_decomposed_train_x(reserved_train_x)
            extraction_decompose_mask = total_reserved_dimension_index
            extraction_important_mask = []

        elif self.extraction_strategy == "Important":
            extraction_decompose_mask = []
            extraction_important_mask = self.get_important_mask(reserved_train_x, different_train_y)
            decomposed_train_x = reserved_train_x[:, extraction_important_mask]
            x_min = np.zeros(decomposed_train_x.shape[1])
            x_max = np.ones(decomposed_train_x.shape[1])
            decomposed_train_x = np.array(decomposed_train_x)

        elif self.extraction_strategy == "Hierarchical":
            # Hierarchical Parameter Selection
            extraction_important_mask = self.get_important_mask(reserved_train_x, different_train_y)
            extraction_decompose_mask = []
            for x in total_reserved_dimension_index:
                if x not in extraction_important_mask:
                    extraction_decompose_mask.append(x)
            # Direct parameters
            important_train_x = reserved_train_x[:, extraction_important_mask]
            # Extracted parameters.
            decomposed_train_x = reserved_train_x[:, extraction_decompose_mask]

            d_x_min, d_x_max = [], []
            if len(extraction_decompose_mask) != 0:
                decomposed_train_x, d_x_min, d_x_max = self.get_decomposed_train_x(decomposed_train_x)
                decomposed_train_x = torch.from_numpy(decomposed_train_x)
                decomposed_train_x = np.array(torch.cat([important_train_x, decomposed_train_x], 1))

            else:
                decomposed_train_x = np.array(important_train_x)

            x_min = [0.0] * important_train_x.shape[1]
            x_max = [1.0] * important_train_x.shape[1]
            x_min.extend(d_x_min)
            x_max.extend(d_x_max)
            x_min = np.array(x_min)
            x_max = np.array(x_max)

        elif self.extraction_strategy == "NoExtraction":
            pass
        return decomposed_train_x, x_min, x_max, extraction_decompose_mask, extraction_important_mask

    def run(self):
        # initial sampling
        self.observe(self.config_space.get_default_configuration())
        for i in range(self.initial_samples - 1):
            self.observe(self.config_space.sample_configuration())

        # TEMT iterations
        for i in tqdm.tqdm(range(self.max_run - self.initial_samples)):
            if self.tmp_dump:
                # dump tmp history in case of unexpected termination
                f = open('history/tmp', 'wb')
                pickle.dump(self.history_container, f, 0)
                f.close()

            while True:

                try:
                    candidate_array = self.get_CEI_candidate()
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


from ConfigSpace import ConfigurationSpace, Configuration
import time

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
    x_3 = sp.Real("x_3", 0, 1, default_value=0)
    space.add_variables([x_1, x_2, x_3])
    tt = TEMTOptimizer(
        similar_factor=0.95,
        objective_function=objective,
        max_run=50,
        initial_samples=10,
        config_space=space,
        task_description="test",
        num_constraints=4,
        tps_constraints=[1, 1, 1, 1],
        acqf_opt_restarts=4,
        acqf_opt_raw_samples=8,
        constraints_dropout=True,
        use_worst_approximation=True,
        filter_gaussian_scale=0.25,
        filter_dist_threshold=0,
        auto_filter=True,
        tmp_dump=False,
        reserve_strategy="Spearman",
        reserve_spearman_factor=0,
        reserved_random_dimensions=3,  # meaningless
        extraction_strategy="Hierarchical",
        extraction_important_strategy="most",
        extraction_important_num_strategy="Fixed",
        extraction_important_num=1,
        fillingin_strategy_factor=0.5
    )

    st = time.time()
    history = tt.run()
    ed = time.time()
    print("Time is", ed - st)
    print('Best is', history.get_best_perf())
