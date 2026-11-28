"""
Example 48 : A language model manages the model
===============================================
A "park warden" looks at Wolf Sheep Predation every 25 ticks and decides
what to do so that neither wolves nor sheep die out.  NetLogo simulates;
Python describes the situation in words, asks for a decision, and applies it.

The warden is any function `decide(situation) -> action`.  Two are given:

* `rule_warden`  : a fixed rule, used by default (no account, no cost);
* `claude_warden`: asks Claude through the Anthropic API.  Each decision is a
  paid request: it is used only with  NETLOGOPY_LLM=1  in the environment,
  with `pip install anthropic` and your credentials (ANTHROPIC_API_KEY).

The same loop works for many agents: build one situation per agent with
`nl.agent_table(...)` and ask for one decision per row.
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy import NetLogo

MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "complexe", "Wolf Sheep",
                     "Wolf Sheep Predation.nlogo")
ACTIONS = {
    "nothing": "",
    "cull-wolves": "ask n-of (count wolves / 3) wolves [ die ]",
    "release-wolves": "create-wolves 15 [ set color black set size 2 set energy 20 setxy random-xcor random-ycor ]",
    "release-sheep": "create-sheep 40 [ set color white set size 1.5 set energy 4 setxy random-xcor random-ycor ]",
}
SYSTEM = ("You are the warden of a nature park simulated in NetLogo (Wolf Sheep Predation). "
          "Your goal is that both wolves and sheep are still there at the end. "
          "Answer with one word, exactly one of: " + ", ".join(ACTIONS) + ".")


def rule_warden(situation):
    """The decision of a fixed rule, from the numbers of the situation."""
    sheep, wolves = situation["sheep"], situation["wolves"]
    if wolves < 15:
        return "release-wolves"
    if sheep < 60:
        return "cull-wolves" if wolves > 40 else "release-sheep"
    return "nothing"


def claude_warden(situation):
    """The decision of Claude; an answer that is not an action counts as "nothing"."""
    import anthropic
    client = anthropic.Anthropic()                 # credentials come from the environment
    response = client.beta.messages.create(
        model="claude-opus-5-5",
        max_tokens=2000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",                       # another model answers if this one declines
        output_config={"effort": "low"},           # a small decision: little reasoning is enough
        system=SYSTEM,
        messages=[{"role": "user", "content":
                   f"Tick {situation['tick']}: {situation['sheep']} sheep, {situation['wolves']} wolves, "
                   f"{situation['grass']} green patches. Sheep {situation['trend']}. What do you do?"}],
    )
    if response.stop_reason == "refusal":
        return "nothing"
    text = "".join(block.text for block in response.content if block.type == "text").strip().lower()
    return next((action for action in ACTIONS if action in text), "nothing")


if __name__ == "__main__":
    warden = claude_warden if os.environ.get("NETLOGOPY_LLM") == "1" else rule_warden
    print("warden:", warden.__name__)
    with NetLogo(MODEL, gui=True) as nl:           # NETLOGOPY_HEADLESS=1: without the window
        nl.random_seed(4)
        nl.setup()
        before = nl.count("sheep")
        for period in range(12):
            nl.go(25)
            sheep, wolves = nl.count("sheep"), nl.count("wolves")
            situation = {"tick": int(nl.ticks), "sheep": sheep, "wolves": wolves,
                         "grass": nl.count("patches", "pcolor = green"),
                         "trend": "are increasing" if sheep > before else "are decreasing"}
            action = warden(situation)
            if ACTIONS[action]:
                nl.command(ACTIONS[action])
            print(f"tick {situation['tick']:4d}: {sheep:4d} sheep, {wolves:4d} wolves -> {action}")
            before = sheep
            if sheep == 0 and wolves == 0:
                break
        alive = nl.count("sheep") > 0 and nl.count("wolves") > 0
        print("both species are still there" if alive else "one species died out")
