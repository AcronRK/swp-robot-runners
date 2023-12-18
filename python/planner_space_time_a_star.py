import math
import random
from typing import List, Tuple, Set
from queue import PriorityQueue
from python.models import Action, BasePlanner
from python.util import getManhattanDistance, get_neighbors
from python.visualization_a_star import AStarVisualizer


class SpaceTimeAStarPlanner(BasePlanner):

    def __init__(self, pyenv=None, visualize=False, animate=False, replanning_period=2, time_horizon=10) -> None:
        super().__init__(pyenv, "Space-Time-A-Star-Planner")
        self.reservation: Set[Tuple[int, int, int]] = set()
        # (cell id 1, cell id 2, timestep relative to current timestep [one_based])
        self.edge_hash_to_robot_id: dict[Tuple[int, int, int], int] = {}
        # (cell id, -1, timestep [one_based]): robot id
        self.next_actions: list[list[int]]
        # next action for each robot
        self.last_planning_step = -math.inf

        self.replanning_period = replanning_period
        self.time_horizon = time_horizon

        self.VISUALIZE = visualize
        if visualize:
            self.visualizer = AStarVisualizer()
            self.visualizer.GENERATE_ANIMATIONS = animate
        random.seed(42)

    def initialize(self, preprocess_time_limit: int):
        return True  # todo: implement preprocessing or optimal pathfinding

    def plan(self, time_limit) -> list[int]:
        if self.last_planning_step + self.replanning_period <= self.env.curr_timestep:
            self.last_planning_step = self.env.curr_timestep
            return self.sample_priority_planner(time_limit)
        else:
            return self.next_actions[self.env.curr_timestep - self.last_planning_step]

    def space_time_plan(
            self,
            start: int,
            start_direct: int,
            end: int,
    ) -> List[Tuple[int, int]]:
        """
        finds the shortest path
        :param start: the start cell index
        :param start_direct: the orientation of the robot
        :param end: the target cell index
        :return: the shortest path if it exists - list of (node index, orientation) tuples
        """
        path = []
        open_list = PriorityQueue()  # list of all cells to look at
        all_nodes = {}  # loc+dict, t
        parent = {}

        if self.VISUALIZE:
            self.visualizer.reset()

        h = getManhattanDistance(self.env, start, end)  # heuristic approximation
        g = 0  # distance traveled
        node_info = (start, start_direct, g, h)
        open_list.put((g + h, h, id(node_info), node_info))
        position_direction_hash = start * 4 + start_direct
        # why start * 4 + start_direct ?
        # because: this results in a unique hash of the postion/orientation (4 orientations -> if orientation changes: at least +1 or +3 at most; if cell changes: at least +4)
        # this is a hash that is used to check if a position/orientation-combination was already looked at
        parent[(position_direction_hash, g)] = None  # safe the parent node

        while not open_list.empty():  # look at all cells in the open list
            if self.VISUALIZE:
                self.visualizer.commit_open_list([(n[3][0], n[3][2]) for n in open_list.queue])
                self.visualizer.new_step()

            node = open_list.get()  # get the node with the lowest f value
            f, h, node_id, current_node_info = node
            position, orientation, g, h = current_node_info
            current_time_step = g  # it is the same, when planning was started in time_step 0
            next_time_step = current_time_step + 1

            if (position * 4 + orientation, g) in all_nodes:
                continue  # skip if this node was already looked at - at the current time step
            all_nodes[(position * 4 + orientation, g)] = current_node_info
            if position == end:
                while True:  # yey, we found a path
                    path.append((current_node_info[0], current_node_info[1]))  # append position, orientation to path
                    current_node_info = parent[(current_node_info[0] * 4 + current_node_info[1], current_node_info[
                        2])]  # previous node is the parent -> get parent by position hash, g (dist from start)
                    if current_node_info is None:
                        break  # start node was reached which has no parent
                path.pop()  # remove the start node
                path.reverse()
                break

            neighbors = get_neighbors(self.env, position, orientation)
            neighbors.append((position, orientation))  # also check if we can wait on the current field
            for neighbor in neighbors:
                # it's not really the neighbor we are checking, it is more the next possible position+orientation
                neighbor_location, neighbor_direction = neighbor

                if self.is_reserved(position, neighbor_location, next_time_step):
                    continue

                neighbor_key = (neighbor_location * 4 + neighbor_direction, next_time_step)

                if neighbor_key in all_nodes:
                    old = all_nodes[neighbor_key]
                    if g + 1 < old[2]:  # todo what exactly is this good for?
                        old = (old[0], old[1], g + 1, old[3], old[4])
                else:
                    next_g = g + 1
                    next_h = getManhattanDistance(self.env, neighbor_location, end)
                    next_node_info = (
                        neighbor_location,
                        neighbor_direction,
                        next_g,
                        next_h,
                    )
                    next_f = next_g + next_h
                    open_list.put(
                        (next_f, next_h, id(next_node_info), next_node_info)
                    )

                    parent[
                        (neighbor_location * 4 + neighbor_direction, next_g)
                    ] = current_node_info

            if self.VISUALIZE:
                self.visualizer.update_data(self.env, open_list, position, orientation, g)
        if self.VISUALIZE:
            self.visualizer.save_visualizations(self.env, start, end)
        return path

    def is_reserved(self, start: int, end: int, time_step: int):
        """
        check if the target cell is already reserved + check if the edge is reserved
        :return: true if move is already reserved
        """
        if end == -1:
            end = start
        if (end, -1, time_step) in self.reservation:
            return True  # the end cell is already reserved

        if (end, start, time_step) in self.reservation:
            return True  # the edge end --to--> start is already reserved in the next timestep
        return False

    def sample_priority_planner(self, time_limit: int):
        # todo only do replanning each nth step
        # todo: stop when time_limit is reached?
        # todo: implement random restarts
        # todo: do replan (or only plan for specific agents) when some agent reached his goal
        self.reservation = set()
        self.edge_hash_to_robot_id = {}

        self.next_actions = [[Action.W.value]*len(self.env.curr_states) for _ in range(self.replanning_period)]

        # reserve waiting cell for all robots that don't have any goals left
        for robot_id in range(self.env.num_of_agents):
            path = []
            if not self.env.goal_locations[robot_id]:
                path.append(
                    (
                        self.env.curr_states[robot_id].location,
                        self.env.curr_states[robot_id].orientation,
                    )
                )
                self.add_reservation(self.env.curr_states[robot_id].location, -1, 1, robot_id)

        # plan and reserve path for one robot at a time
        for robot_id in range(self.env.num_of_agents):
            path = []
            if self.env.goal_locations[robot_id]:
                path = self.space_time_plan(  # get the shortest possible path
                    self.env.curr_states[robot_id].location,
                    self.env.curr_states[robot_id].orientation,
                    self.env.goal_locations[robot_id][0][0]
                )

            last_loc = self.env.curr_states[robot_id].location
            if path:
                # convert the path to actions
                prev_loc = self.env.curr_states[robot_id].location
                prev_ori = self.env.curr_states[robot_id].orientation
                for i in range(min(len(path), self.replanning_period)):
                    # todo compare with previous not with current state
                    new_location = path[i][0]
                    new_orientation = path[i][1]
                    if new_location != prev_loc:
                        self.next_actions[i][robot_id] = Action.FW.value
                    elif new_orientation != prev_ori:
                        incr = new_orientation - prev_ori
                        if incr == 1 or incr == -3:
                            self.next_actions[i][robot_id] = Action.CR.value
                        elif incr == -1 or incr == 3:
                            self.next_actions[i][robot_id] = Action.CCR.value
                    prev_loc = new_location
                    prev_ori = new_orientation
                # reserve the path
                time_step = 1
                for step in range(self.time_horizon):
                    if step < len(path):
                        p = path[step]
                    else:
                        p = path[-1]  # take the last position if path ends before time horizon

                    self.add_reservation(last_loc, p[0], time_step, robot_id)
                    last_loc = p[0]
                    time_step += 1
            if not path:
                # todo: make the path finding always return a valid path if possible
                #  (does not have to reach the goal but should avoid collisions)
                # there is no path for robot i -> he will wait -> reserve his waiting position BUT:
                # it is possible that the waiting cell is already reserved -> the robot that reserved the cell has to be stopped
                # to prevent a crash
                for step in range(self.replanning_period):
                    waiting_position = (last_loc, -1, step + 1)
                    if self.is_reserved(*waiting_position):
                        # check who reserved it and cancel his actions
                        self.handle_conflict(*waiting_position)
                    else:
                        self.add_reservation(*waiting_position, robot_id)

        return self.next_actions[0]

    def add_reservation(self, start: int, end: int, time_step: int, robot_index: int):
        """
        add a path to the reservation table
        :param start: start cell index
        :param end: end cell index: -1 if same as start
        :param time_step: reservation timestep
        :param robot_index: id of the reserving robot
        """
        if end == -1:
            end = start
        cell_hash = (end, -1, time_step)
        self.reservation.add(cell_hash)  # reserve the end cell itself
        self.edge_hash_to_robot_id[cell_hash] = robot_index  # to make it easy to lookup which robot reserved which cell
        if start != end:
            edge_hash = (start, end, time_step)
            self.reservation.add(edge_hash)  # reserve the edge
            self.edge_hash_to_robot_id[edge_hash] = robot_index  # to make it easy to lookup which robot reserved which edge

    def handle_conflict(self, start: int, end: int, time_step: int):
        # todo: revoke all the reservations of the robot that reserved (start, end, time_step)
        # todo: check if there is an easy & quick reroute of the colliding robot possible
        colliding_robot_id = self.edge_hash_to_robot_id[(start, end, time_step)]
        self.revoke_all_reservations_of_robot(colliding_robot_id)
        for step in range(self.replanning_period):
            self.next_actions[step][colliding_robot_id] = Action.W.value  # make colliding robot wait
            # if the colliding robot which will now wait would collide with another robot -> stop the other robot also
            stopped_robot_location = self.env.curr_states[colliding_robot_id].location
            wait_cell_hash_of_stopped_robot = (stopped_robot_location, -1, step + 1)
            if self.is_reserved(*wait_cell_hash_of_stopped_robot):
                self.handle_conflict(*wait_cell_hash_of_stopped_robot)
            self.add_reservation(*wait_cell_hash_of_stopped_robot, colliding_robot_id)

    def revoke_all_reservations_of_robot(self, robot_id: int):
        """
        remove all reservations of a robot
        :param robot_id: id of the robot
        """
        for edge_hash, r_id in list(self.edge_hash_to_robot_id.items()):
            if r_id == robot_id:
                self.reservation.remove(edge_hash)
                del self.edge_hash_to_robot_id[edge_hash]
