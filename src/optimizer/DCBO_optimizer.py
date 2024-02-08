from gpytorch import ExactMarginalLogLikelihood

from src.optimizer.MTBO_optimizer import MTBOOptimizer
import torch
from botorch.fit import fit_gpytorch_mll

DEVICE = torch.device("cpu")


# Dynamic Constrained BO,
class DCBOOptimizer(MTBOOptimizer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def build_multi_task_model(self):

        # Obtain train_x and train_y from history_container
        train_x = self.history_container.get_train_x().to(DEVICE)

        train_obj = self.history_container.get_train_obj()
        train_obj = torch.unsqueeze(train_obj, dim=1)

        # scaling the input objective function to zero mean and unit variance.
        train_obj = (train_obj - train_obj.mean()) / train_obj.std()

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

        # Identify redundant constraints using shape-based clustering
        # and automatically determine the number of clusters by adjusting Sihouette Coefficient
        if self.constraints_dropout:
            different_train_constraints = self.get_compressed_constraints(filtered_constraints)
        else:
            different_train_constraints = filtered_constraints

        # Concatenate train_obj and compressed_train_constarints to obtain a complete train_y
        train_y = torch.cat((train_obj, different_train_constraints), dim=1).to(DEVICE)

        # If there are feasible observations, take the minimum objective value as min_f
        # If no constraints are met, assign a large integer, to guide CEI search in the feasible region.
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
        build Multi-Task GP to model correlations among objective and constraint functions
        
        """
        from botorch.models import KroneckerMultiTaskGP
        gp = KroneckerMultiTaskGP(train_x, train_y).to(DEVICE)

        mll = ExactMarginalLogLikelihood(gp.likelihood, gp).to(DEVICE)
        output = gp(train_x)
        loss = -mll(output, train_y)
        print('MTGP initial_train_loss=', loss)
        from botorch.fit import fit_gpytorch_mll_torch
        fit_gpytorch_mll(mll, optimizer=fit_gpytorch_mll_torch, optimizer_kwargs={'step_limit': 500})
        # fit_gpytorch_mll(mll, optimizer_kwargs={'timeout_sec': 5})

        print('Iter %d/%d - Loss: %.3f   noise: %.3f' % (
            50, 50, loss.item(),
            gp.likelihood.noise.item()
        ))
        output = gp(train_x)
        loss = -mll(output, train_y)
        print('MTGP final_train_loss=', loss)

        gp.eval()
        gp.likelihood.eval()
        return gp, different_train_constraints.shape[1], min_f

    def get_compressed_constraints(self, full_train_constraints):
        constraints = torch.t(full_train_constraints)
        clusters = self.do_shape_based_clustering(constraints)
        compressed_constraints = self.get_conservative_prototype(clusters)
        return compressed_constraints

    def do_shape_based_clustering(self, full_train_constraints):
        clusters = []
        constraint_length = full_train_constraints.shape[1] - 1
        assert constraint_length > 1

        x = self.history_container.get_train_x()
        x_shape_sequence = torch.empty((constraint_length, x.shape[1]), dtype=torch.float64)

        for i in range(len(x_shape_sequence)):
            x_shape_sequence[i] = x[i + 1] - x[i]

        for constraint in full_train_constraints:
            constraint_shape = torch.empty(constraint_length, dtype=torch.float64)

            for i in range(constraint_length):
                constraint_shape[i] = constraint[i + 1] - constraint[i]

            constraint_shape = torch.cat((x_shape_sequence, constraint_shape.unsqueeze(1)), dim=1)
            clusters.append([(constraint, constraint_shape)])  # 初始化时，每个任务为独立的一个簇

        """
        clusters:
        list of cluster
        
        cluster:
        list of (constraint, constraint_shape)
        
        """

        clusters_with_sc = []
        while len(clusters) != 1:  # cluster aggregation until all clusters merge into one cluster.
            print("Cluster Num:", len(clusters), "SC:", self.calculate_sihouette_coefficient(clusters))

            clusters_with_sc.append([clusters, self.calculate_sihouette_coefficient(clusters)])
            src_cluster = None
            dst_cluster = None
            highest_similarity = -1.01

            for i in range(len(clusters)):
                for j in range(i + 1, len(clusters)):
                    similarity = self.get_cluster_similarity(clusters[i], clusters[j])
                    if similarity > highest_similarity:
                        highest_similarity = similarity
                        src_cluster = i
                        dst_cluster = j

            next_clusters = []
            for i in range(len(clusters)):
                if i == src_cluster:
                    new_cluster = []
                    new_cluster.extend(clusters[src_cluster])
                    new_cluster.extend(clusters[dst_cluster])
                    next_clusters.append(new_cluster)
                elif i != dst_cluster:
                    next_clusters.append(clusters[i])
            clusters = next_clusters

        # Find the number of clusters that maximizes the Silhouette Coefficient (SC)
        best_sc = -2
        best_clusters = None
        for i in range(len(clusters_with_sc)):
            if clusters_with_sc[i][1] >= best_sc:
                best_sc = clusters_with_sc[i][1]
                best_clusters = clusters_with_sc[i][0]

        clusters = best_clusters

        # Remove the shape sequences stored in the clusters variable
        res = []
        for i in range(len(clusters)):
            res.append([])
            # point:tuple (constraint, shape)
            for point in clusters[i]:
                p = point[0]
                res[i].append(p)
        return res

    def get_cluster_similarity(self, cluster_a, cluster_b):
        # cluster similarity: the average shape-based similarities among each pair of elements within two clusters.
        similarity_sum = 0
        total_pairs = len(cluster_a) * len(cluster_b)
        highest_similarity = -1.1
        lowest_similarity = 1.1
        for constraint_a in cluster_a:
            for constrain_b in cluster_b:
                similarity_tmp = self.get_shape_based_similarity(constraint_a[1], constrain_b[1])
                similarity_sum += similarity_tmp
                if similarity_tmp > highest_similarity:
                    highest_similarity = similarity_tmp
                if similarity_tmp < lowest_similarity:
                    lowest_similarity = similarity_tmp

        return similarity_sum / total_pairs

    def get_shape_based_similarity(self, constraint_shape_1, constraint_shape_2):
        similarity_sequence = torch.cosine_similarity(constraint_shape_1, constraint_shape_2, dim=-1)
        return torch.mean(similarity_sequence)

    def calculate_sihouette_coefficient(self, clusters):
        if len(clusters) < 2:
            raise NotImplementedError
        sc, element_count = 0, 0
        for i in range(len(clusters)):
            # Iterate through each cluster
            if len(clusters[i]) == 1:  # For single-element clusters, SC=0
                sc += 0
                element_count += 1
            else:
                # Iterate through each element within a cluster
                for j in range(len(clusters[i])):
                    # calculate a, the average dissimilarity within the cluster
                    a = 0
                    count = 0
                    for k in range(len(clusters[i])):
                        if j != k:
                            a += 1 - self.get_shape_based_similarity(clusters[i][j][1], clusters[i][k][1])
                            count += 1
                    a = a / count

                    # calculate b.
                    min_dist = 10000
                    for other_cluster_i in range(len(clusters)):
                        ave_dist = 0
                        if other_cluster_i != i:
                            for k in range(len(clusters[other_cluster_i])):
                                ave_dist += 1 - self.get_shape_based_similarity(clusters[i][j][1],
                                                                                clusters[other_cluster_i][k][1])

                            ave_dist = ave_dist / len(clusters[other_cluster_i])
                            if ave_dist < min_dist:
                                min_dist = ave_dist
                    if max(a, min_dist) == 0:
                        sc += 0
                    else:
                        sc += (min_dist - a) / (max(a, min_dist))
                    element_count += 1
        ave_sc = sc / element_count
        return ave_sc

    def get_conservative_prototype(self, clusters, *args, **kwargs):
        # Within each cluster, the final prototype is the worst value among all observations.
        """
        clusters:[[1d row tensor, tensor,...,],[],...]
        """
        res = []
        for cluster in clusters:
            worst_constraint = cluster[0].clone()
            for i in range(len(cluster)):
                for j in range(clusters[0][0].shape[0]):
                    if worst_constraint[j] > cluster[i][j]:
                        worst_constraint[j] = cluster[i][j]
            worst_constraint = worst_constraint.tolist()
            res.append(worst_constraint)
        res = torch.t(torch.tensor(res, dtype=torch.float64))
        return res


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
    x_1 = sp.Real("x_1", 0, 1, default_value=0)
    x_2 = sp.Real("x_2", 0, 1, default_value=0)
    x_3 = sp.Real("x_3", 0, 1, default_value=1)
    space.add_variables([x_1, x_2, x_3])
    tt = DCBOOptimizer(
        similar_factor=0.99,
        objective_function=objective,
        max_run=10,
        initial_samples=5,
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
        tmp_dump=False
    )

    st = time.time()
    history = tt.run()
    ed = time.time()
    print("Time is", ed - st)
    print('Best is', history.get_best_perf())
