import os
import random
import time
import unittest
from copy import deepcopy
from queue import PriorityQueue

from matplotlib import pyplot as plt

from planner_space_time_a_star import SpaceTimeAStarPlanner
from python.test_util_functions import plot_distance_map
from test_utils import grids_to_env, update_env, print_grid, animate_grid, \
    get_test_env_and_targets_from_config_file
from util import get_neighbors, DistanceMap, convert_1d_to_2d_coordinate
from models import Env, Action, Heuristic, AstarHighLevelPlannerType


class PlannerTest(unittest.TestCase):
    def setUp(self):
        random.seed(42)

    def get_test_env(self) -> Env:
        grid = [  # 0 - empty; 1 - wall; "<i><o>" i - robot nr (has to be bigger than 0) o - orientation (<>v^)
            [0, 0000, 0, 0],
            [0, "1>", 1, 0],
            [0, 0000, 1, 0],
            [0, 0000, 0, 0],
        ]
        goal_grid = [
            [0, 0, 0, 0],  # 0 - empty; 1-infinity - goal of robot 1 - inf
            [0, 0, 0, 1],  # goal of robot 1 (goals have to be the robot
            [0, 0, 0, 0],
            [0, 0, 0, 0],
        ]
        return grids_to_env(grid, goal_grid, "small_test_map")

    def get_huge_test_env(self):
        grid = [  # 0 - empty; 1 - wall; "<i><o>" i - robot nr (has to be bigger than 0) o - orientation (<>v^)
            [0, 0, 0, 0, 0, 0000, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0000, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, "1>", 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0000, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0000, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0000, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0000, 1, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0000, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0000, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0000, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0000, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0000, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        ]
        goal_grid = [
            # 0 - empty; 1-infinity - goal of robot 1 - inf
            # goal of robot 1 (goals have to be the robot
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        ]
        return grids_to_env(grid, goal_grid, "huge_test_map")

    def test_get_neighbors(self):
        env = self.get_test_env()
        first_robot_state = env.curr_states[0]
        neighbors = get_neighbors(env, first_robot_state.location, first_robot_state.orientation)
        # robot is currently at cell 5 with orientation 0 (east)
        # -> neighbors should be the positions after move fw / turn left / right
        self.assertListEqual(neighbors, [(5, 3), (5, 1)])

    def test_basic_planning_one_step(self):
        planner = SpaceTimeAStarPlanner(visualize=True, animate=True)
        planner.env = env = self.get_test_env()
        print_grid(env)
        actions = planner.plan(None)
        env = update_env(env, actions)
        print_grid(env)
        self.assertEqual(actions[0], Action.CCR.value)

    def test_basic_planning_huge_map(self):
        planner = SpaceTimeAStarPlanner(visualize=True, animate=False, restarts=False)
        planner.env = env = self.get_huge_test_env()
        print_grid(env)
        actions = planner.plan(None)
        env = update_env(env, actions)
        print_grid(env)
        self.assertIn(actions[0], [Action.FW.value, Action.CCR.value])

    def test_basic_planning_two_robots(self):
        grid = [
            [0000, 0, 0000, 0],
            ["1>", 0, "2<", 0],
            [0000, 0, 0000, 0]
        ]
        goal_grid = [
            [0, 0, 0, 0],
            [2, 0, 0, 1],
            [0, 0, 0, 0]
        ]
        env = grids_to_env(grid, goal_grid)
        planner = SpaceTimeAStarPlanner()
        planner.env = env

        print_grid(env)
        actions = planner.plan(None)
        env = update_env(env, actions)
        print_grid(env)
        self.assertEqual(actions[0], Action.FW.value)
        actions = planner.plan(None)
        env = update_env(env, actions)
        print_grid(env)

    def test_avoid_edge_collision(self):
        grid = [
            ["1>", "2<"]
        ]
        goal_grid = [
            [2, 1]
        ]
        env = grids_to_env(grid, goal_grid)
        planner = SpaceTimeAStarPlanner()
        planner.env = env
        actions = planner.plan(None)
        self.assertListEqual(actions, [Action.W.value, Action.W.value])

    def test_avoid_cell_collision(self):
        grid = [
            ["1>", 0, "2<"]
        ]
        goal_grid = [
            [2, 0, 1]
        ]
        env = grids_to_env(grid, goal_grid)
        planner = SpaceTimeAStarPlanner()
        planner.env = env
        actions = planner.plan(None)
        # they should wait, because there is no valid path
        self.assertEqual(actions, [Action.W.value, Action.W.value])

    def test_wait_until_blocking_robot_moved(self):
        grid = [
            [0, 0000, 0],
            [0, 0000, "2<"],
            [0, "1^", 0]
        ]
        goal_grid = [
            [0, 1, 0],
            [0, 2, 0],
            [0, 0, 0]
        ]
        env = grids_to_env(grid, goal_grid)
        planner = SpaceTimeAStarPlanner()
        planner.env = env
        actions = planner.plan(None)
        self.assertEqual(Action(actions[1]), Action.W)

    def test_multiple_steps_multiple_robots(self):
        grid = [
            [0, 0000, 1, 0],
            [0, 0000, 1, 0],
            [0, "2>", 1, "1v"],
            [0, 0000, 0, 0]
        ]
        goal_grid = [
            [0, 0, 0, 2],
            [0, 1, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0]
        ]
        env = grids_to_env(grid, goal_grid, "multiple_steps_multiple_robots")
        planner = SpaceTimeAStarPlanner(replanning_period=2)
        planner.env = env
        all_envs = [deepcopy(env)]
        print_grid(env)
        while True:
            actions = planner.plan(None)
            env = update_env(env, actions)
            print([Action(a).name for a in actions])
            print_grid(env)
            all_envs.append(deepcopy(env))
            if all(a == Action.W.value for a in actions):
                break
        animate_grid(all_envs)
        for robot_state, goal in zip(env.curr_states, env.goal_locations):
            self.assertEqual(robot_state.location, goal[0][0])

    def test_time_horizon_deadlock_avoidance(self):
        # why is there a deadlock for 3, 5 and 4, 4? because robot 1 wants to go to the left and robot
        # 2 has no way that does not lead to a collision when he reaches the left wall
        # fix:
        # - random restarts - (heuristic like "robot nearest to its goal first" would also fail here!
        # - increase time horizon
        # 4 - 4 deadlock: idea: preserve all cells where it is clear that the robot cannot escape in one move
        #   otherwise we can end up in an unnecessary deadlock
        # todo: after implementing random restarts for 3 - 5 it's not a deadlock anymore, but a loop :(
        #  fix would be prioritizing the robot that is closer to its goal
        grid = [
            [0, 0000, 0, 0, 0, 0, 0, 0, 0, 0, 0000, 0],
            [0, 0000, 1, 1, 1, 1, 1, 1, 1, 1, 0000, 0],
            [0, "2>", 0, 0, 0, 0, 0, 0, 0, 0, "1<", 0],
            [0, 0000, 1, 1, 1, 1, 1, 1, 1, 1, 0000, 0]
        ]
        goal_grid = [
            [0, 0000, 0, 0, 0, 0, 0, 0, 0, 0, 0000, 0],
            [0, 0000, 0, 0, 0, 0, 0, 0, 0, 0, 0000, 0],
            [1, 0000, 0, 0, 0, 0, 0, 0, 0, 0, 0000, 2],
            [0, 0000, 0, 0, 0, 0, 0, 0, 0, 0, 0000, 0]
        ]
        for replanning_period, time_horizon, expected_actions in [[3, 5, (Action.FW, Action.FW)],
                                                                  [4, 4, (Action.FW, Action.FW)],
                                                                  [4, 8, (Action.CR, Action.FW)]]:
            print(replanning_period, time_horizon)
            env = grids_to_env(grid, goal_grid, "hallway")
            planner = SpaceTimeAStarPlanner(replanning_period=replanning_period, time_horizon=time_horizon,
                                            visualize=False, restarts=True)
            planner.env = env
            all_envs = [deepcopy(env)]
            actions = planner.plan(None)
            print([Action(a) for a in actions])
            env = update_env(env, actions)
            all_envs.append(deepcopy(env))
            self.assertEqual(Action(actions[0]), expected_actions[0])
            self.assertEqual(Action(actions[1]), expected_actions[1])
            for i in range(20):
                actions = planner.plan(None)
                # print([Action(a) for a in actions])
                env = update_env(env, actions)
                # print_grid(env)
                all_envs.append(deepcopy(env))
                if all(a == Action.W.value for a in actions):
                    break
            animate_grid(all_envs)

    def test_deadlock_avoidance_when_minor_robot_needs_2_steps_head_start(self):
        grid = [
            [0, 1, 1, 0, 0],
            [0, "1>", "2<", 0, 0]
        ]
        goal_grid = [
            [0, 0, 0, 0, 0],
            [2, 0, 0, 1, 0],
        ]
        env = grids_to_env(grid, goal_grid, "small_hallway_with_right_padding")
        planner = SpaceTimeAStarPlanner(replanning_period=99, time_horizon=99, restarts=False, visualize=False)
        planner.env = env
        all_envs = [deepcopy(env)]
        actions = planner.plan(None)
        self.assertEqual(Action(actions[0]), Action.W)
        self.assertIn(Action(actions[1]), [Action.CR, Action.CCR])
        env = update_env(env, actions)
        all_envs.append(deepcopy(env))
        while True:
            actions = planner.plan(None)
            env = update_env(env, actions)
            all_envs.append(deepcopy(env))
            if all(a == Action.W.value for a in actions):
                break
        animate_grid(all_envs)

    def test_deadlock_avoidance_when_minor_robot_needs_3_steps_head_start(self):
        grid = [
            [0, 1, 1, 0],
            [0, "1^", "2<", 0]
        ]
        goal_grid = [
            [0, 0, 0, 0],
            [2, 0, 0, 1],
        ]
        # todo for this to work we have to give the second robot more time to "run away"
        #  (not enough steps to turn AND go up, when reaching the wall)
        # this configuration leads to a deadlock independent of the priority:
        # the robot with the higher prio will plan its path and will perform a forward move
        # the second robots can't go out of the first robots way
        # (because it would take 3 steps to turn 180 degrees and move forward)
        env = grids_to_env(grid, goal_grid, "small_hallway")
        planner = SpaceTimeAStarPlanner(replanning_period=99, time_horizon=99, restarts=True, visualize=False)
        planner.env = env
        all_envs = [deepcopy(env)]
        actions = planner.plan(None)
        print([Action(a) for a in actions])
        env = update_env(env, actions)
        all_envs.append(deepcopy(env))
        while True:
            actions = planner.plan(None)
            env = update_env(env, actions)
            all_envs.append(deepcopy(env))
            if all(a == Action.W.value for a in actions):
                break
        animate_grid(all_envs)

    def test_random_restarts(self):
        # @formatter:off
        grid = [
            [0, 0000,    0, 0, 0, 0, 0, 0, 0, 0, 0000, 0],
            [0, 0000,    0, 0, 0, 0, 0, 0, 0, 1, 0000, 0],
            [0,    1,    1, 1, 1, 1, 1, 1, 1, 1, 0000, 0],
            [0, "2>", "3>", 0, 0, 0, 0, 0, 0, 0, "1<", 0],
            [0,    1,    1, 1, 1, 1, 1, 1, 1, 1, 0000, 0]
        ]
        goal_grid = [
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 3],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        ]
        # @formatter:off
        env = grids_to_env(grid, goal_grid, "multiple_steps_multiple_robots")
        planner = SpaceTimeAStarPlanner(replanning_period=8, time_horizon=20, restarts=False)
        planner.env = env
        all_envs = []
        print_grid(env)
        #self.assertEqual(Action(actions[0]), Action.CR)
        #self.assertEqual(Action(actions[1]), Action.FW)
        #self.assertEqual(Action(actions[2]), Action.FW)
        while True:
            actions = planner.plan(None)
            print([Action(a).name for a in actions])
            env = update_env(env, actions)
            print_grid(env)
            all_envs.append(deepcopy(env))
            if all(a == Action.W.value for a in actions):
                break
        animate_grid(all_envs, "without_restarts")
        for robot_state, goal in zip(env.curr_states, env.goal_locations):
            self.assertEqual(robot_state.location, goal[0][0])

    def test_random_20_map(self):
        path = os.path.join(os.path.dirname(__file__), "../example_problems/random.domain/random_400.json")
        env, tasks = get_test_env_and_targets_from_config_file(path)
        next_task_index = env.num_of_agents

        planner = SpaceTimeAStarPlanner(replanning_period=4, time_horizon=8, restarts=False,
                                        heuristic=Heuristic.TRUE_DISTANCE,
                                        high_level_planner=AstarHighLevelPlannerType.PRIORITY_DETOUR)
        planner.env = env
        print_grid(env)
        all_envs = [deepcopy(env)]
        for _ in range(100):
            actions = planner.plan(None)
            print([Action(a).name for a in actions])
            env, next_task_index = update_env(env, actions, tasks, next_task_index)
            #print_grid(env)
            all_envs.append(deepcopy(env))
            if all(a == Action.W.value for a in actions):
                break
        animate_grid(all_envs)

    def test_city_map(self):
        map = "../example_problems/game.domain/brc202d_200.json"
        env, tasks = get_test_env_and_targets_from_config_file(map)
        next_task_index = env.num_of_agents
        print_grid(env)
        planner = SpaceTimeAStarPlanner(replanning_period=1, time_horizon=8, restarts=False, heuristic=Heuristic.TRUE_DISTANCE)
        planner.env = env
        #planner.precompute_heuristic_values()
        action = planner.plan(None)
        print(action)
        env, next_task_index = update_env(env, action, tasks, next_task_index)

    def test_dist_map(self):
        map = "../example_problems/warehouse.domain/warehouse_small_50.json"
        env, tasks = get_test_env_and_targets_from_config_file(map)
        print_grid(env)
        print(convert_1d_to_2d_coordinate(1240, env.cols))
        print(convert_1d_to_2d_coordinate(1216, env.cols))
        with open("/Users/maxehrlicherschmidt/projects/swp-robot-runners/distance_map.pkl", "rb") as f:
            import pickle
            target, close_list, distances, last_start = pickle.load(f)
        distance_map = DistanceMap(1216, env)
        distance_map.target = target
        print(target)
        distance_map.close_list = close_list
        distance_map.distance_map = distances
        distance_map.last_start = last_start
        distance_map.open_list = PriorityQueue()

        plot_distance_map(distance_map.distance_map, env)

        d = distance_map.get_distance(env, 1240, 0)
        print(d)



    def test_compare_heuristic_performance_random_20_map(self):
        for map, time_horizon in [("../example_problems/random.domain/random_20.json", 5), ("../example_problems/random.domain/random_200.json", 10)]:
            replanning_period = 1
            path = os.path.join(os.path.dirname(__file__), map)
            env, tasks = get_test_env_and_targets_from_config_file(path)
            next_task_index = env.num_of_agents
            processing_times = {}
            for heuristic in [Heuristic.MANHATTAN, Heuristic.TRUE_DISTANCE]:
                planner = SpaceTimeAStarPlanner(replanning_period=replanning_period, time_horizon=time_horizon, restarts=False,
                                                          heuristic=heuristic, )
                local_env = deepcopy(env)
                planner.env = local_env
                for _ in range(100):
                    # measure time for planning
                    start = time.time()
                    actions = planner.plan(None)
                    planning_time = time.time() - start
                    processing_times.setdefault(heuristic, []).append(planning_time)
                    local_env, next_task_index = update_env(local_env, actions, tasks, next_task_index)

                #for robot_state, goal in zip(local_env.curr_states, local_env.goal_locations):
                #    self.assertEqual(robot_state.location, goal[0][0])
                # New Plotting section for Bar Chart
            colors = ['blue', 'orange']  # Add more colors if you have more heuristics
            num_iterations = len(processing_times[Heuristic.MANHATTAN])  # Assuming all heuristics have the same number of iterations

            # Set up the plot
            fig, ax = plt.subplots(figsize=(15, 5))

            # Width of a bar
            width = 0.35

            # Creating bars for each heuristic at each iteration
            for i in range(num_iterations):
                for j, heuristic in enumerate(Heuristic):
                    if heuristic in processing_times:
                        # Calculate the position of the bar for this heuristic at this iteration
                        x_pos = i + (j - len(Heuristic)/2) * width
                        # Draw the bar
                        ax.bar(x_pos, processing_times[heuristic][i], width, color=colors[j], label=heuristic.name if i == 0 else "")

            # Add some text for labels, title, and custom x-axis tick labels, etc.
            ax.set_xlabel('Iteration')
            ax.set_ylabel('Processing Time (seconds)')
            map_name = map.split("/")[-1].split("_")[0]
            agent_count = map.split("/")[-1].split("_")[1].split(".")[0]
            ax.set_title(f"Processing Times by Heuristic per Iteration - map: {map_name}, agents: {agent_count}, time horizon: {time_horizon}, replanning period: {replanning_period}")

            # Setting the x-ticks to be in the middle of the group of bars for each iteration
            # ticks for each 10th step
            ax.set_xticks(range(0, num_iterations, 10))
            ax.set_xticklabels(range(1, num_iterations + 1, 10))
            #ax.set_xticks(range(num_iterations))
            #ax.set_xticklabels(range(1, num_iterations + 1))

            # Adding a legend
            # To avoid duplicate labels in the legend, we create custom legend entries
            from matplotlib.lines import Line2D
            legend_elements = [Line2D([0], [0], color=colors[i], lw=4, label=heuristic.name) for i, heuristic in enumerate(Heuristic) if heuristic in processing_times]
            ax.legend(handles=legend_elements)

            plt.grid(True)
            plt.show()

