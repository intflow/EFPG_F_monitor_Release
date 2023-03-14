import subprocess
from subprocess import Popen, PIPE
import configs
import requests
from requests.auth import HTTPBasicAuth
import threading
import multiprocessing
import getpass
import natsort
import json
import getmac
import time
import socket
import shutil
import os
import datetime as dt
import json
import copy
import pytz
import logging
import firmwares_manager
from dateutil import parser


current_dir = os.path.dirname(os.path.abspath(__file__))

def create_run_with_log_file(file_path, run_sh_name):
    run_log_command = f"#!/bin/bash\nbash {run_sh_name} 1> {file_path} 2>&1"
    run_with_log_sh_name = os.path.splitext(run_sh_name)[0] + "_with_log.sh"
    with open(run_with_log_sh_name, "w") as f:
        f.write(run_log_command)
    subprocess.run(f"docker cp {run_with_log_sh_name} efhall_test:/opt/nvidia/deepstream/deepstream/sources/apps/sample_apps", shell=True)
    os.remove(run_with_log_sh_name)
    return run_with_log_sh_name

def get_log_file_list(dirpath):
    file_list = [x for x in os.listdir(dirpath) if os.path.splitext(x)[-1] == ".log"]
    file_list.sort(key = lambda f: os.path.getmtime(os.path.join(dirpath, f)), reverse=True)
    
    return file_list

def get_dir_size(path='.'):
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    return total

def check_log_dir_vol():
    python_log("\nCheck log dir volume!")    
    
    if get_dir_size(configs.log_save_dir_path_host) >= configs.log_max_volume:
        log_f_list = get_log_file_list(configs.log_save_dir_path_host)
    
        while get_dir_size(configs.log_save_dir_path_host) >= configs.log_max_volume:
            if len(log_f_list) == 0:
                break
            # python_log(f"Remove \"{os.path.join(configs.log_save_dir_path_host, log_f_list[-1])}\"")
            os.remove(os.path.join(configs.log_save_dir_path_host, log_f_list[-1]))
            del log_f_list[-1]
    python_log("Done!\n")
    
def log_dir_vol_manage(now_dt, LOG_DIR_CHECK):
    if now_dt.minute == 0 and now_dt.second == 0:
    # if now_dt.second == 0:
        if LOG_DIR_CHECK == False:
            check_log_dir_vol()
            LOG_DIR_CHECK = True
    else:
        LOG_DIR_CHECK = False  
    
    return LOG_DIR_CHECK 

def port_status_check(port):
    try:
        res = subprocess.check_output("netstat -ltu | grep {}".format(port), shell=True)
        res = res.decode().split('\n')[:-1]
    except subprocess.CalledProcessError:
        res = []
        
    if len(res) > 0 and res[0].split()[-1] == "LISTEN":
        return True
    else:
        return False
    
def port_process_kill(port):
    try:
        output = subprocess.check_output("echo 9121intflow3121# | sudo -S netstat -nap | grep {}".format(port), stderr=subprocess.PIPE, shell=True)
        output = output.decode().split('\n')[:-1]
        # python_log(output)
    except subprocess.CalledProcessError:
        output = []
    
    if len(output) > 0:
        output = output[0].split()[-1].split('/')[0]
        subprocess.run("echo 9121intflow3121# | sudo -S kill -9 {}".format(output), shell=True)
        # python_log(f'kill {output}')

def kill_edgefarm():
    subprocess.run(f"docker exec -it {configs.container_name} bash ./kill_edgefarm.sh", shell=True)
    
def rm_docker():
    subprocess.run(f"docker stop {configs.container_name} ", shell=True)
    
def run_docker(docker_image, docker_image_id):
    firmwares_manager.copy_firmwares()
    device_install()
    fan_speed_set(configs.FAN_SPEED)
    if docker_image == None or docker_image_id == None:
        for i in range(10):
            python_log("\nNo Docker Image...\n")
        return -1
    # if (check_deepstream_status()): # engine 켜져있다면
    #     rm_docker()
    
    run_docker_command = "docker run -dit "\
                        + "--rm "\
                        + f"--name={configs.container_name} "\
                        + "--net=host "\
                        + "--privileged "\
                        + "--ipc=host "\
                        + "--runtime nvidia "\
                        + "-v /edgefarm_config:/edgefarm_config "\
                        + "-v /home/intflow/works:/works "\
                        + "-w /opt/nvidia/deepstream/deepstream-6.0/sources/apps/sample_apps "\
                        + f"{docker_image_id} bash "
                        # + "{} bash".format(lastest_docker_image_info[1])
    python_log(run_docker_command)
    python_log(f"Docker Image : {docker_image}\n")
    subprocess.call(run_docker_command, shell=True)
    python_log("\nDocker run!\n")

def run_SR_docker():
    run_sh_name = "run_SR.sh"
    
    os.makedirs(configs.log_save_dir_path_host, exist_ok=True)

    KST_timezone = pytz.timezone('Asia/Seoul')
    now_kst = dt.datetime.now().astimezone(KST_timezone)
    
    file_name = now_kst.strftime("%Y%m%d_%H%M%S_SmartRec.log")
    file_path = os.path.join(configs.log_save_dir_path_docker, file_name)
    
    run_with_log_sh_name = create_run_with_log_file(file_path, run_sh_name)
        
    remove_SR_vid()
    # file_list = os.listdir(configs.recordinginfo_dir_path)
    # subprocess.run(f"docker exec -dit {configs.container_name} bash ./run_SR.sh 1> {file_path} 2>&1", shell=True)
    # subprocess.run(f"docker exec -dit {configs.container_name} bash ./run_SR_with_log.sh 1> {file_path} 2>&1", shell=True)
    subprocess.run(f"docker exec -dit {configs.container_name} bash {run_with_log_sh_name}", shell=True)
    python_log("\nDocker  Smart Record run!\n")
    # python_log(f"\nThe real-time log is being saved at \"{os.path.join(configs.log_save_dir_path_host, file_name)}\"\n")
def export_model(docker_image, docker_image_id, mode=""):
    deepstream_exec=False
    SR_exec=False
    for line in Popen(['ps', 'aux'], shell=False, stdout=PIPE).stdout:
        result = line.decode('utf-8')
        if result.find('deepstream-SR')>1: # deepstream이 ps에 있는지 확인
            SR_exec=True
            python_log("smart record 실행중")
            break  
        if result.find('deepstream-custom-pipeline')>1: # deepstream이 ps에 있는지 확인
            deepstream_exec=True
            python_log("file sink 가 실행중")
            break  
    print("export model!\n")
    if not deepstream_exec and not SR_exec:
        subprocess.run(f"docker exec -dit {configs.container_name} bash export_model.sh ", shell=True)
    # print(run_docker_command)
def edgefarm_config_check():
    # /edgefarm_config 가 없으면 전체 복사
    if os.path.isdir("/edgefarm_config") == False:
        subprocess.run("sudo mkdir /edgefarm_config", shell=True)
        print("make directory /edgefarm_config")
    subprocess.run("sudo chown intflow:intflow -R /edgefarm_config", shell=True)
    
    git_edgefarm_config_path = os.path.join(current_dir, "edgefarm_config")
    
    # 모델 관련 파일이 있나 검사. 하나라도 없으면 복사해주고 모델 export
    model_related_list = ['model', 'model/intflow_model.onnx', 'model/intflow_model.engine']
    no_model = False
    for m_i in model_related_list:
        tmp_p = os.path.join(configs.local_edgefarm_config_path, m_i)
        if not os.path.exists(tmp_p):
            no_model = True
    if no_model:    
        model_update(mode='sync')
def model_update(mode=""):
    local_model_file_path = os.path.join(configs.local_edgefarm_config_path, configs.local_model_file_relative_path)
    
    # 인터넷 안되면 monitor 에 있는 model 복사
    if not configs.internet_ON:
        subprocess.run(f"sudo cp {os.path.join(current_dir, 'edgefarm_config/model/intflow_model.onnx')} {local_model_file_path}")
    else:    
        # /edgefarm_config/model 디렉토리가 없으면 생성.
        if not os.path.exists(os.path.join(configs.local_edgefarm_config_path, "model")):
            os.makedirs(os.path.join(configs.local_edgefarm_config_path, "model"), exist_ok=True)
            
        serial_number = read_serial_number()
        
        print("Start Model Update!")
        
        model_file_name = f"{serial_number}/{configs.server_model_file_name}"
        
        # 서버에서 모델 파일 복사해오기
        # copy_to(os.path.join(git_edgefarm_config_path, "model/intflow_model.onnx"), os.path.join(configs.local_edgefarm_config_path, "model/intflow_model.onnx"))
        subprocess.run(f"aws s3 cp s3://{configs.server_bucket_of_model}/{model_file_name} {local_model_file_path}", shell=True)
    
    docker_image, docker_image_id = find_lastest_docker_image(configs.docker_repo)
    # onnx to engine
    export_model(docker_image, docker_image_id, mode=mode)
    # # 버전 파일 복사.
    if mode == "sync" : print("\nModel Update Completed")    
def run_file_deepstream_docker():
    run_sh_name = "run_filesink.sh"
    # check_SR_file()
    
    os.makedirs(configs.log_save_dir_path_host, exist_ok=True)
    
    KST_timezone = pytz.timezone('Asia/Seoul')
    now_kst = dt.datetime.now().astimezone(KST_timezone)
    
    file_name = now_kst.strftime("%Y%m%d_%H%M%S_FileSink.log")
    file_path = os.path.join(configs.log_save_dir_path_docker, file_name)
    
    run_with_log_sh_name = create_run_with_log_file(file_path, run_sh_name)
    # subprocess.run(f"docker exec -dit {configs.container_name} bash ./run_filesink.sh", shell=True)
    subprocess.run(f"docker exec -dit {configs.container_name} bash {run_with_log_sh_name}", shell=True)
    python_log("\nDocker run!\n")
    python_log(f"\nThe real-time log is being saved at \"{os.path.join(configs.log_save_dir_path_host, file_name)}\"\n")
def check_SR_file():
    file_list = os.listdir('/edgefarm_config/Recording/')
    file_list.sort(key=lambda x: os.stat(x).st_mtime)
    SR_list=[]
    for file_name in file_list:
        if file_name[:3]=="SR_":
            if int(file_name[3]) in SR_list:
                python_log(file_name+"중복제거 ")
                os.remove(os.path.join('/edgefarm_config/Recording/',file_name))
            else:    
                SR_list.append(int(file_name[3]))
            

def fan_speed_set(speed):
    # 팬 속도
    subprocess.run("echo 9121intflow3121# | sudo -S sh -c 'echo {} > /sys/devices/pwm-fan/target_pwm'".format(speed), stderr=subprocess.PIPE, shell=True)

## 실행 중이면 True, 실행 중이 아니면 False 반환.
def check_deepstream_status():
    res = subprocess.check_output("docker ps --format \"{{.Names}}\"", shell=True)
    res = str(res, 'utf-8').split("\n")[:-1]
    
    # python_log(res)

    if configs.container_name in res:
        return True
    else:
        return False
    

def current_running_image(docker_image_head):
    res = subprocess.check_output("docker images --filter=reference=\"{}*\" --format \"{{{{.Tag}}}} {{{{.ID}}}}\"".format(docker_image_head), shell=True)
    res = str(res, 'utf-8').split("\n")[:-1]
    res = [i.split(" ") for i in res]
    res = natsort.natsorted(res, key = lambda x: x[0], reverse=True)
    # python_log(res)

    c_image_id = None
    c_image_name = None
    c_res = subprocess.check_output("docker ps --format \"{{.Names}} {{.Image}}\"", shell=True)
    c_res = str(c_res, 'utf-8').split("\n")[:-1]
    c_res = [i.split(" ") for i in c_res]
    # python_log(c_res)

    for container_name, image in c_res:
        if container_name == configs.container_name:
            c_image_id = image
            # python_log(c_image_id)
        
    if c_image_id is not None:
        for image_name, image_id in res:
            if image_id == c_image_id:
                # python_log(image_name)
                c_image_name = image_name
    
    return c_image_name

def find_lastest_docker_image(docker_image_head, mode=0):
    res = subprocess.check_output("docker images --filter=reference=\"{}*\" --format \"{{{{.Tag}}}} {{{{.ID}}}}\"".format(docker_image_head), shell=True)
    res = str(res, 'utf-8').split("\n")[:-1]
    if len(res) == 0:
        return [None, None]
    
    res = [i.split(" ") for i in res]

    res = natsort.natsorted(res, key = lambda x: x[0], reverse=True)
    
    if mode == 1:
        python_log(f"\n{docker_image_head} docker image list")
        for i in res:
            python_log('  ', i)
    
    return res[0]

def docker_pull(docker_repo, last_docker_image_dockerhub):
    if configs.docker_id == None or configs.docker_pw == None:
        configs.docker_id = input("UserID for 'https://hub.docker.com/': ")
        configs.docker_pw = getpass.getpass("Password for 'https://hub.docker.com/': ")        
    subprocess.run(f"docker login docker.io -u \"{configs.docker_id}\" -p \"{configs.docker_pw}\"", shell=True)
    subprocess.run("docker pull {}".format(docker_repo + ":" + last_docker_image_dockerhub), shell=True)
    subprocess.run("docker logout", shell=True)

def docker_image_tag_api(image):
    docker_api_host = "https://registry.hub.docker.com"
    path = "/v1/repositories/" + image + "/tags"
    url = docker_api_host + path
    configs.docker_id = input("UserID for 'https://hub.docker.com/': ")
    configs.docker_pw = getpass.getpass("Password for 'https://hub.docker.com/': ")
    # python_log(url)
    try:
        response = requests.get(url,auth = HTTPBasicAuth(configs.docker_id, configs.docker_pw))

        # python_log("response status : %r" % response.status_code)
        return response.json()
    except Exception as ex:
        python_log(ex)
        return None
    
def search_dockerhub_last_docker_image(docker_repo, tag_header):
    # res = docker_image_tag_api('intflow/edgefarm')
    res = docker_image_tag_api(docker_repo)
    
    current_image = find_lastest_docker_image(docker_repo + ":" + tag_header)[0]
    
    if res is not None:
        image_tag_list = []

        for each_r in res:
            # python_log(each_r["name"])
            # if "hallway_dev" in each_r["name"]:
            if tag_header in each_r["name"]:
                # python_log(each_r["name"])
                image_tag_list.append(each_r["name"])
                
        image_tag_list = natsort.natsorted(image_tag_list, key = lambda x: x, reverse=True)
        
        if len(image_tag_list) > 0:
            if current_image is None:
                update_history = len(image_tag_list)
            else:
                if current_image in image_tag_list:
                    update_history = image_tag_list.index(current_image)
                else:
                    update_history = -1
            return [image_tag_list[0], update_history]
        else:
            return ["None", -1]
    else:
        return ["None" -1]

def send_api(path, mac_address):
    url = configs.API_HOST + path + '/' + mac_address

    python_log(url)
    
    try:
        response = requests.get(url)

        # python_log("response status : %r" % response.status_code)
        return response.json()
    except Exception as ex:
        python_log(ex)
        return None
def check_aws_install():
    res = os.popen('which aws').read()

    if "/usr/local/bin/aws" in res:
        print("AWS CLI installed")
        pass
    else:
        print("Install AWS CLI ...")
        subprocess.run("bash ./aws_cli_build.sh", shell=True)
        
    mac_address = getmac.get_mac_address()
    serial_number=read_serial_number()
        
    akres = send_ak_api("/device/upload/key", mac_address, serial_number)

    if not os.path.isdir("/home/intflow/.aws"):
        os.makedirs("/home/intflow/.aws", exist_ok=True)
        
    subprocess.run('sudo chown intflow:intflow /home/intflow/.aws -R', shell=True)

    with open("/home/intflow/.aws/credentials", "w") as f:
        f.write(f"[default]\naws_access_key_id = {akres['access']}\naws_secret_access_key = {akres['secret']}\n")
def get_local_model_mtime():
    local_model_file_path = os.path.join(configs.local_edgefarm_config_path, configs.local_model_file_relative_path)
    
    if not os.path.exists(local_model_file_path):
        return None
    
    kst = pytz.timezone('Asia/Seoul')
    
    last_modified_local = os.path.getmtime(local_model_file_path)

    last_modified_local = dt.datetime.fromtimestamp(last_modified_local)
    last_modified_local = kst.localize(last_modified_local)    
    
    return last_modified_local
def send_ak_api(path, mac_address, serial_number):
    url = configs.API_HOST2 + path + '/' 
    content={}
    content['mac_address']=mac_address
    content['serial_number']=serial_number
    print(url)
    
    try:
        # response = requests.post(url, data=json.dumps(metadata))
        response = requests.put(url, json=content)

        print("response status : %r" % response.status_code)
        if response.status_code == 200:
            # return True
            return response.json()
        else:
            # return False
            return None
        # return response.json()
    except Exception as ex:
        print(ex)
        # return False
        return None 
def send_json_api(path, mac_address,serial_number,firmware_version):
    url = configs.API_HOST2 + path + '/' 
    content={}
    content['mac_address']=mac_address
    content['serial_number']=serial_number
    content['version']=firmware_version
    print(url)
    
    try:
        # response = requests.post(url, data=json.dumps(metadata))
        response = requests.put(url, json=content)

        print("response status : %r" % response.status_code)
        if response.status_code == 200:
            # return True
            return response.json()
        else:
            # return False
            return None
        # return response.json()
    except Exception as ex:
        print(ex)
        # return False
        return None
def key_match(src_key, src_data, target_data):
    if src_key in configs.key_match_dict:
        target_key = configs.key_match_dict[src_key]
        if target_key in target_data:
            target_val = target_data[target_key]
            python_log(f"{src_key} : {src_data[src_key]} -> {target_val}")
            src_data[src_key] = target_val 
            
def read_serial_number():
    with open(os.path.join(configs.local_edgefarm_config_path, "serial_number.txt"), 'r') as mvf:
        serial_numbertxt = mvf.readline()
    return serial_numbertxt.split('\n')[0]

def read_firmware_version():
    with open(os.path.join(configs.firmware_dir, "__version__.txt"), 'r') as mvf:
        firmware_versiontxt = mvf.readline()
    return firmware_versiontxt.split('\n')[0]

def device_install():
    try:
        # mac address 뽑기
        mac_address = getmac.get_mac_address()
        check_aws_install()
        mkdir_logs()
        serial_number=read_serial_number()
        firmware_version=read_firmware_version()
        docker_repo = configs.docker_repo
        docker_image, docker_image_id = find_lastest_docker_image(docker_repo)
        docker_image_tag_header = configs.docker_image_tag_header
        e_version=docker_image.replace(docker_image_tag_header+'_','').split('_')[0]
        device_info=send_json_api(configs.access_api_path, mac_address, serial_number, firmware_version)
        
        # print(device_info)
        
        # 기존 파일들 삭제
        if os.path.isdir(configs.roominfo_dir_path):
            shutil.rmtree(configs.roominfo_dir_path)    
        os.mkdir(configs.roominfo_dir_path)

        params_of_room = [
            "id", 
            "device_id", 
            "name", 
            "weight_bias", 
            "age", 
            "chessboard_cm", 
            "chessboard_px",
            "vpi_k1",
            "vpi_k2",
            "x_focus",
            "y_focus",
            "x_pad",
            "y_pad",
            "x_rotate",
            "y_rotate",
            "x_scale",
            "y_scale",
            "zx_perspect",
            "zy_perspect",
            "detection_area",
            "food_area"
            ]

        key_match = {
            "chessboard_cm" : "grow_width_cm",
            "chessboard_px" : "grow_width_pixel"
        }

        total_room_info_list = []

        for a_dict in device_info['camera_list']:
            rtsp_value = a_dict["rtsp"]
            b_dict_index = None
            
            for i, b_dict in enumerate(total_room_info_list):
                if b_dict["rtsp"] == rtsp_value:
                    b_dict_index = i
                    break
            
            if b_dict_index is None:
                b_dict = {"rtsp": rtsp_value, "info": []}
                total_room_info_list.append(b_dict)
            else:
                b_dict = total_room_info_list[b_dict_index]
            
            b_dict_info = {}
            for key, value in a_dict.items():
                if key in params_of_room:
                    if key in key_match.keys():
                        key = key_match[key]
                    b_dict_info[key] = value
            b_dict["info"].append(b_dict_info)

        for i, item in enumerate(total_room_info_list):
            file_name = f"room{i}.json"
            
            with open(os.path.join(configs.roominfo_dir_path, file_name), "w", encoding="utf-8") as f:
                json.dump(item, f, ensure_ascii=False)  
                
    except Exception as e:
        python_log(e)
    
def docker_log_end_print():
    print("\n===========================================")
    print("       View docker log mode End")
    print("===========================================\n")
    # control_thread_mutex.release()
    
def docker_log_view():
    ## docker log 보는 subprocess 실행
    docker_log = subprocess.Popen(f"docker logs -f -t --since=24h {configs.container_name}", stdout=subprocess.PIPE, shell=True)

    while docker_log.poll() == None:
        out = docker_log.stdout.readline()
        python_log(out.decode(), end='')

    docker_log_end_print()
def model_update_check(check_only = False):
    if not configs.internet_ON:
        return
     
    print("Check Model version...")
    lastest = True
    
    serial_number = read_serial_number()

    model_file_name = f"{serial_number}/{configs.server_model_file_name}"
    
    print(f"s3://{configs.server_bucket_of_model}/{model_file_name}")

    try:
        res = subprocess.check_output(f"aws s3api head-object --bucket {configs.server_bucket_of_model} --key {model_file_name}", shell=True)
    except Exception as e:
        print("Can not find model file in server!")
        return False
        
    res_str = res.decode()

    model_file_metadata = json.loads(res_str)
    model_file_metadata["LastModified"]

    last_modified_server_string = model_file_metadata["LastModified"]
    last_modified_server = parser.parse(last_modified_server_string)

    kst = pytz.timezone('Asia/Seoul')

    last_modified_server = last_modified_server.astimezone(kst)
    last_modified_local = get_local_model_mtime()
    if last_modified_local is None:
        print("Can not find model file in local!")
        return False

    print(f"  server : {last_modified_server}")
    print(f"  local  : {last_modified_local}")

    #date_kst
    if last_modified_server > last_modified_local:
        print("Model Update required...")
        lastest = False
    elif last_modified_server <= last_modified_local:
        print("Lastest version of model")

    if not check_only and lastest == False:
        # 혹시 엣지팜 켜져있으면 끄기.
        model_update(mode='sync')
        
    return True

def show_docker_images_list(docker_image_head):
    subprocess.run("docker images --filter=reference=\"{}*\"".format(docker_image_head), shell=True)

def port_info_set():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    configs.last_ip=s.getsockname()[0].split('.')[-1]

    with open(configs.edgefarm_port_info_path, 'r') as port_info_f:
        content = port_info_f.readlines()
        num_line = len(content)

        if configs.last_ip is not None:
            configs.PORT = int(configs.last_ip + str(configs.device_socket_port_end))
            configs.http_server_port = int(configs.last_ip + str(configs.http_server_port_end))
            if num_line >= 3:
                udp_host = "224.224.255." + configs.last_ip + "\n"
                content[2] = udp_host

                configs.engine_socket_port = configs.last_ip + str(configs.engine_socket_port_end)

                if num_line >= 4:
                    content[3] = configs.engine_socket_port + "\n"
                    content[4] = str(configs.PORT) + "\n"
                    content[5] = str(configs.http_server_port) + "\n"
                else:
                    content.append(configs.engine_socket_port + "\n")
                    content.append(str(configs.PORT) + "\n")
                    content.append(str(configs.http_server_port) + "\n")

    with open(configs.edgefarm_port_info_path, 'w') as port_info_f:
        port_info_f.writelines(content)
        
        
def send_meta_api(cam_id_, data):
    uri_param = "/camera/hour/data"
    url = configs.API_HOST + uri_param + '/' + str(cam_id_)

    python_log(url)
    
    try:
        # response = requests.post(url, data=json.dumps(metadata))
        response = requests.post(url, json=data)

        python_log("response status : %r" % response.status_code)
        if response.status_code == 200:
            return True
        else:
            return False
        # return response.json()
    except Exception as ex:
        python_log(ex)
        return False
        # return None
def metadata_info():
    meta_f_list = os.listdir(configs.METADATA_DIR)
    for i, each_f in enumerate(meta_f_list):
        with open(os.path.join(configs.METADATA_DIR, each_f), "r") as json_file:
            content = json.load(json_file)
# 메타정보 보내는
def metadata_send():
    meta_f_list = os.listdir(configs.METADATA_DIR)
    now_dt = dt.datetime.now().astimezone(dt.timezone(dt.timedelta(hours=9))) # 2022-10-21 17:22:32
    now_dt_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    now_dt_str_for_vid_name = now_dt.strftime("%Y%m%d%H")
    res = [False for i in range(len(meta_f_list))]

    for i, each_f in enumerate(meta_f_list):
    # each_f = meta_f_list[0]
        content_og = None
        with open(os.path.join(configs.METADATA_DIR, each_f), "r") as json_file:
            content = json.load(json_file)
            content_og = copy.deepcopy(content)
            cam_id = -1
            source_id = -1
            if "updated" not in content: # updated 없으면 패스
                continue
            if content["updated"] == False: # updated False 면 패스
                continue
            else: # updated 있으면
                content.pop('updated') # updated pop
                content_og["updated"] = False # False 로 변경.
            # if "created_datetime" not in content:
            content["created_datetime"] = now_dt_str
            content_og["created_datetime"] = now_dt_str
            if "cam_id" in content:
                cam_id = content.pop('cam_id')
            if "source_id" in content:
                source_id = content.pop('source_id')
            overlay_vid_name = "efpg_" + now_dt_str_for_vid_name + f"_{source_id}CH.mp4"
            content['video_path'] = overlay_vid_name
            # python_log(content)          
            if send_meta_api(cam_id, content) == True:
                res[i] = True
                
        # 보내고 난 다음에 updated 가 False 로 바꾼 것들을 저장.
        if content_og is not None:
            with open(os.path.join(configs.METADATA_DIR, each_f), "w") as json_file:
                json.dump(content_og, json_file)
                
    return res
def mkdir_logs():
    import os
    import stat
    log_folder = "../logs"
    if not os.path.exists(log_folder):
        os.makedirs(log_folder, mode=0o777)
        os.chmod(log_folder, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

def python_log(debug_print):
    if isinstance(debug_print, str):
        now_dt = dt.datetime.now().astimezone(dt.timezone(dt.timedelta(hours=9)))
        formattedDate = now_dt.strftime("%Y%m%d_%H0000")
        f = open('../logs/'+formattedDate+"_monitor.log", "a", encoding="UTF8")
        formattedDate2 = now_dt.strftime("%Y%m%d_%H%M%S")
        f.write(debug_print+'\n')
        f.close()
def internet_check():
    try:
        # connect to the host -- tells us if the host is actually reachable
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        print("Check Internet : Success")
        return True
    except socket.timeout:
        print("Check Internet : Failed(Timeout)")
        return False
    except:
        print("Check Internet : Failed")
        return False         
# deepstream 실행 횟수 json을 0으로 클리어 하는
def clear_deepstream_exec():
    with open(configs.deepstream_num_exec, 'r') as f:

        json_data = json.load(f)

    json_data['deepstream_smartrecord']=0
    json_data['deepstream_filesink']=0
    json_data['DB_insert']=0
    
    
    
    with open(configs.deepstream_num_exec, 'w') as f:
        json.dump(json_data, f)

        
def remove_SR_vid(): # 레코드 폴더에 있는 SR 이름 다 지우기 
    file_list = os.listdir('/edgefarm_config/Recording/')
    for file_name in file_list:
        if file_name[:3]=="SR_":
            python_log('file 지우겠습니다.'+file_name)
            os.remove(os.path.join('/edgefarm_config/Recording/',file_name))
def matching_cameraId_ch():
    matching_dic={}
    now_dt = dt.datetime.now().astimezone(dt.timezone(dt.timedelta(hours=9)))
    for each_f in os.listdir(configs.roominfo_dir_path):
        if 'room' in each_f:
            ch_num=each_f.split('room')[1][0]
            json_f = open(os.path.join(configs.roominfo_dir_path, each_f), "r")
            content = json.load(json_f)
            json_f.close()
            matching_dic[ch_num]=content["id"]
    file_list = os.listdir(configs.recordinginfo_dir_path)
    for file_name in file_list:
        if 'CH' in file_name:
            file_ch=file_name.split('CH')[0][-1] 
            if file_ch in matching_dic.keys():
                cam_id=id=matching_dic[file_ch]  
                if now_dt.minute==0 or now_dt.minute>=58:
                    break
                else:
                    subprocess.run("aws s3 mv "+configs.recordinginfo_dir_path+"/"+file_name+" s3://intflow-data/"+str(cam_id)+"/"+file_name, shell=True)
                
# deepstream 실행 횟수를 체킹하는
def check_deepstream_exec(first_booting):
    python_log('check_deepstream_exec')
    
    first_booting=False
    if first_booting:
        
        python_log('처음시작 실행')
        run_SR_docker()
    time.sleep(5) # 5초 지연.
    while (True):
        deepstream_exec=False
        SR_exec=False
        aws_exec=False
        now_dt = dt.datetime.now().astimezone(dt.timezone(dt.timedelta(hours=9)))
        # python_log("30초마다 체크")
        # if now_dt.hour==23 and now_dt.minute==50:
        #     python_log('deepstream exec cnt를 초기화 하고 reboot 하겠습니다.')
        #     with open(configs.deepstream_num_exec, 'r') as f:

        #         json_data = json.load(f)

        #     json_data['deepstream_smartrecord']=0
        #     json_data['deepstream_filesink']=0
        #     json_data['DB_insert']=0
        #     with open(configs.deepstream_num_exec, 'w') as f:
        #         json.dump(json_data, f)
        #     subprocess.run("echo 9121intflow3121# | sudo -S reboot", shell=True) 
        for line in Popen(['ps', 'aux'], shell=False, stdout=PIPE).stdout:
            result = line.decode('utf-8')
            if result.find('deepstream-SR')>1: # deepstream이 ps에 있는지 확인
                SR_exec=True
                python_log("smart record 실행중")
                break  
            if result.find('deepstream-custom-pipeline')>1: # deepstream이 ps에 있는지 확인
                deepstream_exec=True
                python_log("file sink 가 실행중")
                break  
        if not deepstream_exec  and now_dt.minute>5: # deepstream이 실행하지 않을때 
            with open(configs.deepstream_num_exec, 'r') as f:

                json_data = json.load(f)

            deepstream_smartrecord = json_data['deepstream_smartrecord']
            deepstream_filesink = json_data['deepstream_filesink']
            DB_insert = json_data['DB_insert']

            if deepstream_smartrecord-1==deepstream_filesink: #스마트레코딩 딥스트립이  파일싱크 딥스트립보다 실행횟수가 많을때 
                
                
                python_log("Smart Recording is over. It's time to run the deepstream file sink.")
                run_file_deepstream_docker()
            if deepstream_smartrecord==deepstream_filesink and deepstream_filesink-1==DB_insert : #스마트레코딩 딥스트립과 파일싱크 딥스트립보다 실행횟수가 같은데 DB 통신 횟수가 적을때 
                
                
                python_log("deepstream file sink is over. It's time to insert DataBase")
            
                ### 데이터 베이스 전송 코드 입력 부분###
                try:
                    metadata_send_res = metadata_send()
                    
                    if True in metadata_send_res:
                        python_log("Database insert successful")
                    else:
                        python_log("Database insert Failed")
                        
                    aws_thread_list = []
                    aws_thread_mutex = threading.Lock()
                    aws_thread_cd = threading.Condition()
                    # aws_thread = threading.Thread(target=check_deepstream_exec, name="check_deepstream_exec_thread", args=(first_booting,))
                    # aws_thread.start()
                    aws_thread_list.append(threading.Thread(target=matching_cameraId_ch, name="check_deepstream_exec_thread", daemon=True))
                    aws_thread_list[0].start()
                    # matching_cameraId_ch()    
                except Exception as e:
                    python_log(e)
                json_data['DB_insert']=DB_insert+1  # DB insert count 하나 추가!
                with open(configs.deepstream_num_exec, 'w') as f:
                    json.dump(json_data, f)
            if deepstream_smartrecord==deepstream_filesink and deepstream_filesink==DB_insert : #스마트레코딩 딥스트립과 파일싱크 딥스트립, DB 통신 횟수 같을때
                
                python_log('모든 작업이 끝났다. 정각까지 기다리는 시간')
        if not SR_exec:

            if now_dt.minute<=4 :
                device_install()
                with open(configs.deepstream_num_exec, 'r') as f:

                    json_data = json.load(f)

                deepstream_smartrecord = json_data['deepstream_smartrecord']
                deepstream_filesink = json_data['deepstream_filesink']
                DB_insert = json_data['DB_insert']                
                python_log("It's time to run Smart Record. ")
                if deepstream_smartrecord!=deepstream_filesink:
                    python_log("오늘의 스마트레코딩 갯수 과 객체검출 영상 횟수가 같지않음 갯수 조정")
                    json_data['deepstream_filesink']=deepstream_smartrecord
                    with open(configs.deepstream_num_exec, 'w') as f:
                        json.dump(json_data, f)
                if deepstream_smartrecord!=DB_insert:
                    python_log("오늘의 스마트레코딩 갯수 과 디비 인설트 횟수가 같지않음 갯수 조정")
                    json_data['DB_insert']=deepstream_smartrecord
                    with open(configs.deepstream_num_exec, 'w') as f:
                        json.dump(json_data, f)
                if deepstream_exec:
                    python_log(" file sink가 실행중입니다. 종료하고 스마트레코딩 실행하겠습니다. ")
                    subprocess.run(f"docker exec -dit {configs.container_name} bash ./kill_filesink.sh", shell=True)     
                if aws_exec:
                    python_log('aws 강제 종료 ')
                    subprocess.run("pkill -9 aws", shell=True)     
                if deepstream_smartrecord!=deepstream_filesink and deepstream_smartrecord!=DB_insert:
                    python_log('루틴 횟수 초기화~')
                    
                    json_data['deepstream_smartrecord']=0
                    json_data['DB_insert']=0
                    json_data['deepstream_filesink']=0
                    with open(configs.deepstream_num_exec, 'w') as f:
                        json.dump(json_data, f)
                run_SR_docker()
        time.sleep(30) # 60초 지연.


if __name__ == "__main__":
    # # mac address 뽑기
    # mac_address = getmac.get_mac_address().replace(':','')

    # # device 정보 받기 (api request)
    # device_info = send_api(configs.server_api_path, "48b02d2ecf8c")
    
    # python_log(device_info)
    # model_update_check()
    device_install()
    # check_deepstream_exec(False)
    # metadata_send()
    # check_aws_install()