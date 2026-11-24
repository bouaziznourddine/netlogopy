"""
Example 35 : Job shop with human operators (simulation + optimisation)
======================================================================
A job shop where each machine has an operator.  The operator's punctuality
(a Markov chain between the machine and three non-productive zones), fatigue
and experience set the processing speed.

NetLogo displays the workshop; Python holds the model and, every REOPT
ticks, re-optimises the queue of each machine.  The same scenario is run
with two strategies (first-in-first-out, and shortest remaining work first)
and the results are compared.  With matplotlib installed, a Gantt chart of
each run is saved in ./netlogopy-output/.
"""
import math, os, random, sys, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy import NetLogo, colors

HORIZON = 300                  # ticks simulated
REOPT = 20                     # re-optimise the queues every REOPT ticks
JOBS_PER_TYPE = 6
ROUTING = {                    # job type -> [(machine, processing time), ...]
    "J1": [("M1", 5), ("M3", 2), ("M2", 4)],
    "J2": [("M2", 3), ("M1", 4), ("M3", 9)],
    "J3": [("M3", 2), ("M2", 2), ("M1", 1)],
}
JOB_COLORS = {"J1": colors.RED, "J2": colors.GREEN, "J3": colors.SKY}
MACHINES = {"M1": (10, 28, "machine"), "M2": (30, 28, "machine2"), "M3": (50, 28, "machine3")}
ZONES = [(8, 52), (20, 52), (32, 52)]          # non-productive zones
STOCK = (52, 52)
# Operator profiles: Markov matrix (state 0 = at the machine, 1..3 = zones),
# fatigue rate while working and recovery rate while away.
PROFILES = {
    "M1": {"P": [[1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0]], "fatigue": 0.010, "recovery": 0.02},
    "M2": {"P": [[.9, .1, 0, 0], [.6, .2, .1, .1], [0, .3, .4, .3], [0, .3, .4, .3]], "fatigue": 0.015, "recovery": 0.03},
    "M3": {"P": [[.8, .2, 0, 0], [.3, .3, .2, .2], [0, .4, .3, .3], [0, .3, .4, .3]], "fatigue": 0.020, "recovery": 0.03},
}


def experience(t):
    """Learning curve (logistic): from 0.7 to 1.5 around tick 120."""
    return 0.7 + 0.8 / (1 + math.exp(-0.04 * (t - 120)))


class Job:
    def __init__(self, nl, name, kind, slot):
        self.name, self.kind, self.step, self.done_at = name, kind, 0, None
        self.turtle = nl.create_turtles(1, "pyturtles", shape="box", size=2, heading=0,
                                        color=JOB_COLORS[kind], xcor=2 + slot * 1.5, ycor=4)[0]

    @property
    def operation(self):
        return ROUTING[self.kind][self.step] if self.step < len(ROUTING[self.kind]) else None

    @property
    def remaining(self):
        return sum(duration for _, duration in ROUTING[self.kind][self.step:])


class Machine:
    def __init__(self, nl, name):
        x, y, shape = MACHINES[name]
        self.name, self.x, self.y, self.profile = name, x, y, PROFILES[name]
        self.queue, self.progress, self.started = [], 0.0, None
        self.state, self.fatigue = 0, 0.0
        self.turtle = nl.create_turtles(1, "pyturtles", xcor=x, ycor=y, shape=shape, size=6,
                                        color=colors.GRAY, heading=0, label=name)[0]
        self.operator = nl.create_turtles(1, "pyturtles", xcor=x, ycor=y + 6, shape="person_0",
                                          size=5, color=colors.ORANGE, heading=0)[0]

    def speed(self, t):
        return max(0.0, experience(t) - self.fatigue)

    def show_queue(self):
        for position, job in enumerate(self.queue):
            job.turtle.setxy(self.x - 4 + 2 * (position % 5), self.y - 6 - 2.5 * (position // 5))
        self.turtle.label = f"{self.name}  Q={len(self.queue)}"


def simulate(nl, strategy, seed, delay):
    """Run the job shop once; return the statistics of the run."""
    rng = random.Random(seed)
    nl.clear_turtles()
    nl.clear_drawing()
    nl.reset_ticks()
    for x, y in ZONES + [STOCK]:
        nl.create_turtles(1, "pyturtles", xcor=x, ycor=y, shape="house", size=5, heading=0,
                          color=colors.BROWN if (x, y) != STOCK else colors.LIME)
    machines = {name: Machine(nl, name) for name in MACHINES}
    jobs = [Job(nl, f"{kind}_{i + 1}", kind, slot)
            for slot, (kind, i) in enumerate((k, i) for k in ROUTING for i in range(JOBS_PER_TYPE))]
    for job in jobs:
        machines[job.operation[0]].queue.append(job)
    for machine in machines.values():
        machine.show_queue()
    nl.create_temporary_plot_pen(strategy)
    nl.set_plot_pen_color(colors.RED if strategy == "fifo" else colors.BLUE)
    gantt, finished = [], 0

    for t in range(HORIZON):
        if strategy == "shortest-remaining" and t % REOPT == 0:
            for machine in machines.values():      # Python "optimiser": keep the job in
                head, rest = machine.queue[:1], machine.queue[1:]   # progress, sort the others
                keep_head = bool(head) and machine.progress > 0
                waiting = rest if keep_head else head + rest
                waiting.sort(key=lambda job: job.remaining)
                machine.queue = (head if keep_head else []) + waiting
                machine.show_queue()

        for machine in machines.values():
            # punctuality: Markov chain of the operator
            state = rng.choices(range(4), weights=machine.profile["P"][machine.state])[0]
            if state != machine.state:
                machine.state = state
                x, y = (machine.x, machine.y + 6) if state == 0 else (ZONES[state - 1][0], ZONES[state - 1][1] - 5)
                machine.operator.setxy(x, y)
            working = state == 0 and bool(machine.queue)
            rate = machine.profile["fatigue"] if working else -machine.profile["recovery"]
            machine.fatigue = 1 - (1 - machine.fatigue) * math.exp(-rate) if working \
                else machine.fatigue * math.exp(rate)
            if not working:
                continue
            job = machine.queue[0]
            if machine.started is None:
                machine.started = t
            machine.progress += machine.speed(t)
            if machine.progress >= job.operation[1]:           # operation finished
                gantt.append((machine.name, job.name, job.kind, machine.started, t + 1))
                machine.queue.pop(0)
                machine.progress, machine.started = 0.0, None
                job.step += 1
                if job.operation is None:
                    job.done_at, finished = t + 1, finished + 1
                    job.turtle.setxy(STOCK[0] - 4 + 1.2 * (finished % 8), STOCK[1] - 5 - 2 * (finished // 8))
                else:
                    machines[job.operation[0]].queue.append(job)
                    machines[job.operation[0]].show_queue()
                machine.show_queue()

        nl.tick()
        nl.plot(finished, plot="My Plot", pen=strategy)
        time.sleep(delay)
        if finished == len(jobs):
            break

    flow = [job.done_at for job in jobs if job.done_at is not None]
    return {"strategy": strategy, "finished": finished, "jobs": len(jobs), "ticks": t + 1,
            "mean flow time": sum(flow) / len(flow) if flow else float("nan"), "gantt": gantt}


def save_gantt(result, folder):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    figure, axis = plt.subplots(figsize=(10, 3))
    palette = {"J1": "tab:red", "J2": "tab:green", "J3": "tab:blue"}
    for machine, job, kind, start, end in result["gantt"]:
        axis.barh(machine, end - start, left=start, color=palette[kind], edgecolor="white")
    axis.set_xlabel("tick")
    axis.set_title(f"Job shop, {result['strategy']}: {result['finished']}/{result['jobs']} jobs")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"job-shop-gantt-{result['strategy']}.png")
    figure.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(figure)
    return path


if __name__ == "__main__":
    with NetLogo(gui=True) as nl:                  # gui=False: same run without the window
        nl.setup()
        nl.set_current_plot("My Plot")
        nl.set_plot_x_range(0, HORIZON)
        nl.set_plot_y_range(0, 3 * JOBS_PER_TYPE)
        results = [simulate(nl, strategy, seed=7, delay=0.02)
                   for strategy in ("fifo", "shortest-remaining")]
        time.sleep(2)

    print(f"{'strategy':20s} finished  ticks  mean flow time")
    for result in results:
        print(f"{result['strategy']:20s} {result['finished']:3d}/{result['jobs']:<3d}  {result['ticks']:5d}  "
              f"{result['mean flow time']:10.1f}")
        chart = save_gantt(result, os.path.join(os.getcwd(), "netlogopy-output"))
        if chart:
            print("  Gantt chart:", chart)
