"""
Example 30 : Networks and layouts
=================================
Build a random network from Python, lay it out with NetLogo's spring layout
and colour the nodes by degree.
"""
import random, time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy import NetLogo, colors

if __name__ == "__main__":
    random.seed(4)
    with NetLogo(gui=True) as nl:
        nl.setup()
        nodes = nl.create_turtles(25, shape="circle", size=2, color=colors.GRAY)

        # Each new node links to two existing ones (preferential attachment)
        targets = [nodes[0], nodes[1]]
        nl.create_link(nodes[0], nodes[1])
        for node in nodes[2:]:
            for other in set(random.sample(targets, 2)):
                node.create_link_with(other)
                targets += [node, other]

        nl.layout_circle("turtles", 20)
        for _ in range(30):
            nl.layout_spring("turtles", "links", spring_constant=0.2, spring_length=6,
                             repulsion_constant=2, iterations=5)
            time.sleep(0.05)

        degrees = nl.of("turtles", "count my-links")
        for node, degree in zip(nodes, degrees):
            node.size = 1 + degree / 2
            node.color = colors.RED if degree >= 6 else colors.SKY
        hub = nodes[degrees.index(max(degrees))]
        print(f"{nl.count('links')} links; the hub is {hub} with {max(degrees):.0f} links")
        print("hub neighbours:", hub.link_neighbors())
        time.sleep(2)
