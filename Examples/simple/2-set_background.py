import time, os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from netlogopy.netlogopy import *

if __name__ == "__main__" :
    netlogo_home = None   # newest NetLogo installed; or e.g. "C:/Program Files/NetLogo 6.2.2"
    n=run_netlogo(netlogo_home)
    # Resize world
    resize_world(n,0,60,0,60)
    # Image shown behind the agents
    path_image = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "netlogopy.png")
    set_background(n,path_image)
    car01=pyturtle(n,x=20,y=20,shape="car",size_shape=4,color=15,name="car01",labelcolor=15)
    
    for i in range(0,10):
        time.sleep(1)
        print("***********  ",i,"  ********")  
    n.close_model()