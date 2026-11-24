# Agents

## Creating and finding agents

```python
wolves = nl.create_turtles(5, "wolves", color=15, size=2)  # breed in plural form
cars = nl.create_turtles(8, "pyturtles", ordered=True)     # create-ordered-turtles
t = nl.turtle(0)                     # any turtle by who number
p = nl.patch(3, 4)
link = nl.create_link(t, wolves[1])  # breed=..., directed=...
```

## Variables

```python
t.xcor, t.heading, t.color, t.label = 10, 90, 15, "hello"   # built-in variables
t["energy"] = 5                      # any variable (turtles-own, breed-own)
t.set(color=55, label_color=45)      # several at once; label_color -> label-color
t.get_many(["xcor", "ycor", "energy"])
```

## Movement and geometry

```python
t.forward(2).right(45).back(1)       # fd, bk, rt, lt, jump, setxy, move_to, face...
t.distance(p), t.towards(wolves[1]), t.patch_here(), t.patch_ahead(1)
t.in_radius(3, "sheep"), t.in_cone(5, 60), t.turtles_here(), t.neighbors()
t.uphill("chemical")                 # uphill, uphill4, downhill, downhill4
t.turtles_at(1, 0), t.patch_at_heading_and_distance(90, 2)
```

## Life and death

```python
babies = t.hatch(2, color=45)        # new Turtle objects
p.sprout(3, "sheep")
t.die(); t.alive                     # False
```

## Links

```python
a, b, c = nl.create_turtles(3)
a.create_link_with(b)                # undirected
a.create_links_to([b, c], "streets") # directed, breeded
a.link_neighbors(), a.my_out_links("streets"), a.out_link_to(b, "streets")
a.is_link_neighbor(b), b.is_in_link_neighbor(a)
link.end1, link.end2, link.other_end(a), link.length
```

## NetLogo code run by an agent

```python
t.ask("rt random 360 fd 1")          # commands run by the agent
t.of("xcor + ycor")                  # reporter evaluated by the agent
```

## Queries on the whole model

```python
nl.turtles()                          # every turtle, sorted by who
nl.turtles("sheep", where="energy > 5")
nl.patches(where="pcolor = green")
nl.links("roads")
nl.count("wolves"), nl.count("patches", "pcolor = green")
nl.ask("sheep with [energy < 2]", "die")
nl.ask(babies, "set color red")       # a list of agents works too
nl.of("turtles", "energy")            # values in the same order as nl.turtles()
nl.one_of("sheep"), nl.n_of(3, "wolves"), nl.max_one_of("sheep", "energy")
nl.breeds()                           # {'turtles': ['sheep', 'wolves'], 'links': []}
```
