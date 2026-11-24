"""
Example 41 : Routing cars on a NetLogo road network
===================================================
NetLogo holds a road network (intersections are turtles, roads are links)
and moves the cars; Python reads the network, computes the shortest routes
(Dijkstra) and gives them to the cars.  Halfway, a road on a car's route is
closed: Python reroutes every car that was going to use it.

Any graph library could take Python's part (networkx, OR-Tools...).
"""
import heapq, os, random, sys, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy import NetLogo, colors

COLUMNS, ROWS, SPACING = 7, 6, 8
SPEED, CLOSE_AT = 0.6, 25
TRIPS = [((0, 0), (6, 5), colors.RED), ((0, 5), (6, 0), colors.ORANGE), ((3, 0), (3, 5), colors.YELLOW)]


def build_network(nl, rng):
    """A jittered grid of intersections; a few roads are missing."""
    nodes = {}
    for column in range(COLUMNS):
        for row in range(ROWS):
            x = 5 + column * SPACING + rng.uniform(-1.5, 1.5)
            y = 8 + row * SPACING + rng.uniform(-1.5, 1.5)
            nodes[column, row] = nl.create_turtles(1, shape="circle", size=1.2, color=colors.GRAY,
                                                   xcor=x, ycor=y)[0]
    for (column, row), node in nodes.items():
        for neighbour in ((column + 1, row), (column, row + 1)):
            if neighbour in nodes and rng.random() > 0.12:
                nl.create_link(node, nodes[neighbour], directed=False, color=colors.GRAY, thickness=0.4)
    return nodes


def read_graph(nl):
    """{who: {who: length}} from NetLogo's open roads, in one call."""
    graph = {}
    for a, b, length in nl.report("[(list [who] of end1 [who] of end2 link-length)] of links "
                                  f"with [color != {colors.RED}]"):
        graph.setdefault(int(a), {})[int(b)] = length
        graph.setdefault(int(b), {})[int(a)] = length
    return graph


def dijkstra(graph, start, goal):
    queue, best, previous = [(0.0, start)], {start: 0.0}, {}
    while queue:
        distance, node = heapq.heappop(queue)
        if node == goal:
            path = [goal]
            while path[-1] != start:
                path.append(previous[path[-1]])
            return path[::-1], distance
        if distance > best[node]:
            continue
        for neighbour, length in graph.get(node, {}).items():
            candidate = distance + length
            if candidate < best.get(neighbour, float("inf")):
                best[neighbour], previous[neighbour] = candidate, node
                heapq.heappush(queue, (candidate, neighbour))
    return None, float("inf")


class Car:
    def __init__(self, nl, origin, goal, color):
        self.nl, self.goal = nl, goal.who
        self.turtle = nl.create_turtles(1, shape="car", size=3, color=color,
                                        xcor=origin.xcor, ycor=origin.ycor)[0]
        self.turtle.pen_size = 2
        self.turtle.pen_down()
        self.route, self.at = [], origin.who

    def plan(self, graph):
        path, length = dijkstra(graph, self.at, self.goal)
        self.route = path[1:] if path else []
        return length

    def drive(self):
        """Move SPEED towards the next intersection; True once arrived."""
        if not self.route:
            return self.at == self.goal
        target = self.nl.turtle(self.route[0])
        self.turtle.face(target)
        distance = self.turtle.distance(target)
        self.turtle.forward(min(SPEED, distance))
        if distance <= SPEED:
            self.at = self.route.pop(0)
        return False


if __name__ == "__main__":
    rng = random.Random(8)
    with NetLogo(gui=True) as nl:                   # the bundled model; gui=False also works
        nl.setup()
        nodes = build_network(nl, rng)
        graph = read_graph(nl)
        cars = [Car(nl, nodes[a], nodes[b], color) for a, b, color in TRIPS]
        for car in cars:
            print(f"car to {car.goal}: route of {car.plan(graph):.1f} patches")

        for tick in range(400):
            if tick == CLOSE_AT:                    # roadworks on the first car's next road
                car = cars[0]
                a, b = car.at, car.route[0]
                road = nl.turtle(a).link_with(nl.turtle(b))
                road.set(color=colors.RED, thickness=1)
                graph = read_graph(nl)
                print(f"tick {tick}: road {a}-{b} closed")
                for other in cars:
                    legs = list(zip([other.at] + other.route, other.route))
                    if not any({x, y} == {a, b} for x, y in legs):
                        continue                    # its route avoids the closed road
                    on_it = {legs[0][0], legs[0][1]} == {a, b}
                    left = other.plan(graph)        # new route from its last intersection
                    if on_it:                       # already on the closed road: go back first
                        other.route.insert(0, other.at)
                    print(f"  car to {other.goal} rerouted: {left:.1f} patches left")
            arrived = [car.drive() for car in cars]
            nl.tick()
            time.sleep(0.02)
            if all(arrived):
                break
        print(f"all cars arrived at tick {nl.ticks:.0f}")
        time.sleep(2)
