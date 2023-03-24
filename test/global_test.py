import threading
import time
from global_test2 import *


def test_thread():
    global test_str
    with control_thread_cd:
        control_thread_cd.wait()
    while(True):
        print(test_str)
        time.sleep(1)
        if test_str[0] == "Bye":
            break

if __name__ == "__main__":
    test_str = ["None"]
    test_th = threading.Thread(target=test_thread)
    control_thread_cd = threading.Condition()
    test_th.start()
    
    time.sleep(2)
    
    test_def1(control_thread_cd)
        
    time.sleep(3)
    # print(f"test_str : Bye")
    # test_str = "Bye"
    test_def2(test_str)
    
    test_th.join()
