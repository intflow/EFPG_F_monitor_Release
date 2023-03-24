#%%
import requests
import json
import natsort
import subprocess

def find_lastest_docker_image(docker_image_head, mode=0):
    res = subprocess.check_output("docker images --filter=reference=\"{}*\" --format \"{{{{.Tag}}}} {{{{.ID}}}}\"".format(docker_image_head), shell=True)
    res = str(res, 'utf-8').split("\n")[:-1]
    if len(res) == 0:
        return []
    
    res = [i.split(" ") for i in res]

    res = natsort.natsorted(res, key = lambda x: x[0], reverse=True)
    
    if mode == 1:
        print(f"\n{docker_image_head} docker image list")
        for i in res:
            print('  ', i)
    
    return res[0]

## 실행 중이면 True, 실행 중이 아니면 False 반환.
def check_deepstream_status():
    res = subprocess.check_output("docker ps --format \"{{.Names}}\"", shell=True)
    res = str(res, 'utf-8').split("\n")[:-1]

    if "efhall_test" in res:
        return True
    else:
        return False

def current_running_image(docker_image_head):
    res = subprocess.check_output("docker images --filter=reference=\"{}*\" --format \"{{{{.Tag}}}} {{{{.ID}}}}\"".format(docker_image_head), shell=True)
    res = str(res, 'utf-8').split("\n")[:-1]
    res = [i.split(" ") for i in res]
    res = natsort.natsorted(res, key = lambda x: x[0], reverse=True)
    # print(res)

    c_image_id = None
    c_image_name = None
    c_res = subprocess.check_output("docker ps --format \"{{.Names}} {{.Image}}\"", shell=True)
    c_res = str(c_res, 'utf-8').split("\n")[:-1]
    c_res = [i.split(" ") for i in c_res]
    # print(c_res)

    for container_name, image in c_res:
        if container_name == "efhall_test":
            c_image_id = image
            # print(c_image_id)
        
    if c_image_id is not None:
        for image_name, image_id in res:
            if image_id == c_image_id:
                # print(image_name)
                c_image_name = image_name
    
    return c_image_name
    

print(current_running_image("intflow/edgefarm:hallway_dev"))
        