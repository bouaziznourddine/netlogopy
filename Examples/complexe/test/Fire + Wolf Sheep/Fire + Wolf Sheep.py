"""Run two NetLogo models at the same time, each in its own process.

Each process has its own Java (JPype), so the models do not interfere.
"""
import multiprocessing
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))
from netlogopy.netlogopy import netlogo_session, run_command


def run_model_in_process(netlogo_home, model_path, lock, output_file_path):
    try:
        with netlogo_session(netlogo_home, model_path, headless=True) as n:
            for i in range(10):
                run_command(n, "go")
                with lock:
                    with open(output_file_path, "a") as f:
                        f.write(f"{model_path} iteration {i}\n")
                print(f"{model_path}  {i}")
    except Exception as e:
        error_message = f"Error in process for model {model_path}: {e}\n"
        with lock:
            with open(output_file_path, "a") as f:
                f.write(error_message)
        print(error_message)


if __name__ == "__main__":
    netlogo_home = "C:/Program Files/NetLogo 6.2.2"   # or None to detect it
    current_dir = os.path.dirname(os.path.abspath(__file__))
    path_model1 = os.path.join(current_dir, "Fire.nlogo")
    path_model2 = os.path.join(current_dir, "Wolf Sheep Predation.nlogo")
    print(f"Model 1 path: {path_model1}")
    print(f"Model 2 path: {path_model2}")

    output_file_path = os.path.join(current_dir, "output.txt")
    lock = multiprocessing.Lock()
    processes = [multiprocessing.Process(target=run_model_in_process,
                                         args=(netlogo_home, path, lock, output_file_path))
                 for path in (path_model1, path_model2)]
    for p in processes:
        p.start()
    for p in processes:
        p.join()
    print("Both models have finished running.")
