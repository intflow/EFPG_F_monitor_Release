from concurrent.futures import thread
import os
import re
import datetime
import subprocess
import time
import requests
import json
import getmac
import threading
import multiprocessing
from queue import Queue
import socket
import struct
import configs
from utils import *
import httpserver


def client_cut(client_socket, client_addr):
    cli_ip, cli_port = client_addr
    print("invalid client! Cut off Connection!")
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0)) # TIME WAIT 남기지 않고 바로 칼같이 끊어버리기 위함.

# binder함수는 서버에서 accept가 되면 생성되는 socket 인스턴스를 통해 client로 부터 데이터를 받으면 echo형태로 재송신하는 메소드이다.
def binder(client_socket, client_addr):
    cli_ip, cli_port = client_addr
    # 커넥션이 되면 접속 주소가 나온다.
    # print('Connected by', client_addr);
    print("\n=======================================================================================")
    print("Client connected IP address = {} : {}".format(cli_ip, cli_port))
    try:
        ## header 검사
        data = client_socket.recv(6)
        header = data.decode()
        addressee = header[0:3] # 수신인 체크.
        if (addressee != 'EFM'): # 처음 전송하는 데이터(header)의 앞 3byte 가 EFM (EdgeFarmMonitor) 가 아니면 접속을 끊어버림.
            client_cut(client_socket, client_addr)
            return 0

        ## 데이터 종류 체크
        data_class = header[3:6] # 보내는 데이터 종류 체크
        if data_class == "RST": # ReStarT 엣지팜 재시작.
            client_socket.sendall(b'y') # 잘 받았다는 신호 전송.

            data = client_socket.recv(1) # 값 기다림.
            val = data.decode()
            if val == '1':
                # ANCHOR : 디바이스 재부팅.
                client_socket.sendall(b'y') # 받을거 다 받았다. 니가 먼저 끊어라 클라이언트야. 라는 메세지 전송.
                if client_socket.recv(1) == b'y': # 클라이언트가 "네 먼저 끊겠습니다" 라고 보내옴.
                    kill_edgefarm() # 엣지팜 먼저 끄기.
                    subprocess.run("echo intflow3121 | sudo -S reboot", shell=True) # 그 다음에 디바이스 재부팅.
                    # subprocess.run("reboot", shell=True) # 그 다음에 디바이스 재부팅.
                else:
                    client_cut(client_socket, client_addr)
                    return 0
            else: # 이상한 값이 들어오면 손절.
                client_cut(client_socket, client_addr)
                return 0
        elif data_class == "SDU": # ReStarT 엣지팜 재시작.
            client_socket.sendall(b'y') # 잘 받았다는 신호 전송.

            data = client_socket.recv(1) # 값 기다림.
            val = data.decode()
            if val == '1':
                # ANCHOR : 디바이스 재부팅.
                client_socket.sendall(b'y') # 받을거 다 받았다. 니가 먼저 끊어라 클라이언트야. 라는 메세지 전송.
                if client_socket.recv(1) == b'y': # 클라이언트가 "네 먼저 끊겠습니다" 라고 보내옴.
                    kill_edgefarm() # 엣지팜 먼저 끄기.
                    docker_repo = configs.docker_repo
                    docker_image_tag_header = configs.docker_image_tag_header
                    docker_image, docker_image_id = find_lastest_docker_image(docker_repo + ":" + docker_image_tag_header)
                    last_docker_image_dockerhub, docker_update_history = search_dockerhub_last_docker_image(docker_repo, docker_image_tag_header)
                    newly_version=last_docker_image_dockerhub.replace(docker_image_tag_header+'_','').split('_')[0]
                    now_version=docker_image.replace(docker_image_tag_header+'_','').split('_')[0]
                    print(newly_version)
                    print(now_version)
                    if docker_image != last_docker_image_dockerhub :
                        print("다름")
                        # subprocess.run("docker pull {}".format(docker_repo + ":" + last_docker_image_dockerhub), shell=True)
                        docker_pull(docker_repo, last_docker_image_dockerhub)
                        subprocess.run("echo intflow3121 | sudo -S reboot", shell=True) # 그 다음에 디바이스 재부팅.
                    else : 
                        print("같음")
                    # subprocess.run("reboot", shell=True) # 그 다음에 디바이스 재부팅.
                else:
                    client_cut(client_socket, client_addr)
                    return 0
            else: # 이상한 값이 들어오면 손절.
                client_cut(client_socket, client_addr)
                return 0
        else: # 데이터 종류가 알맞지 않으면 손절.
            client_cut(client_socket, client_addr)
            return 0

    except:
        # 접속이 끊기면 except가 발생한다.
        print("except : " , client_addr)
    finally:
        # 접속이 끊기면 socket 리소스를 닫는다.
        client_socket.close()
        print("Client disconnected IP address = {} : {}".format(cli_ip, cli_port))
        print("=======================================================================================")
    

def socket_server_run():
    # 소켓을 만든다.
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 소켓 레벨과 데이터 형태를 설정한다.
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # 서버는 복수 ip를 사용하는 pc의 경우는 ip를 지정하고 그렇지 않으면 None이 아닌 ''로 설정한다.
    # 포트는 pc내에서 비어있는 포트를 사용한다. cmd에서 netstat -an | find "LISTEN"으로 확인할 수 있다.
    server_socket.bind((configs.HOST, configs.PORT))
    # server 설정이 완료되면 listen를 시작한다.
    server_socket.listen()
    try:
        # 서버는 여러 클라이언트를 상대하기 때문에 무한 루프를 사용한다.
        while True:
            # client로 접속이 발생하면 accept가 발생한다.
            # 그럼 client 소켓과 addr(주소)를 튜플로 받는다.
            client_socket, client_addr = server_socket.accept()
            # 쓰레드를 이용해서 client 접속 대기를 만들고 다시 accept로 넘어가서 다른 client를 대기한다.
            th = threading.Thread(target=binder, args = (client_socket, client_addr,))
            th.start()
    except:
        print("\n\nFailed Socket Server Start!\n\n")
    finally:
        # 에러가 발생하면 서버 소켓을 닫는다.
        server_socket.close()
    
def key_match(src_key, src_data, target_data):
    if src_key in configs.key_match_dict:
        target_key = configs.key_match_dict[src_key]
        if target_key in target_data:
            target_val = target_data[target_key]
            print(f"{src_key} : {src_data[src_key]} -> {target_val}")
            src_data[src_key] = target_val 

# folder scale check
def get_dir_size(path='.'):
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    return total

def get_size(path='.'):
    if os.path.isfile(path):
        return os.path.getsize(path)
    elif os.path.isdir(path):
        return get_dir_size(path)

def folder_value_check(_time, _path_, ALLOW_CAPACITY, BOOL_HOUR_CHECK, FIRST_BOOT_REMOVER = False):
    
    if FIRST_BOOT_REMOVER:
        try: # 이 자리에 시간마다 처리하고 싶은 코드를 집어 넣으면 됨.
            # folder_scale = get_size(_path_) / (1024.0 * 1024.0 * 1000.0)
            diskInfo  = os.statvfs('/')
            used      = diskInfo.f_bsize * (diskInfo.f_blocks - diskInfo.f_bavail) / (1024.0 * 1024.0 * 1000.0)
            free      = diskInfo.f_bsize * diskInfo.f_bavail / (1024.0 * 1024.0 * 1000.0)
            total     = diskInfo.f_bsize * diskInfo.f_blocks / (1024.0 * 1024.0 * 1000.0)
            print(f"used : {used} | free : {free} | total : {total}")
            if free < total * ALLOW_CAPACITY_RATE:
                max_day_cnt = 30
                while (max_day_cnt >= -1):
                    
                    # folder 내부 날짜순으로 제거
                    os.system(f"echo intflow3121 | sudo -S find {_path_} -name '*.mp4' -ctime +{max_day_cnt}" + " -exec rm -rf {} \;")
                    os.system(f"echo intflow3121 | sudo -S find {_path_} -name '*.jpeg' -ctime +{max_day_cnt}" + " -exec rm -rf {} \;")
                    os.system(f"echo intflow3121 | sudo -S find {_path_} -name '*.jpg' -ctime +{max_day_cnt}" + " -exec rm -rf {} \;")
                    # command = f"find {_path_} -type f -ctime +{max_day_cnt}" + " -exec rm -rf {} \;"
                    # os.popen("sudo -S %s"%(command), 'w').write('intflow3121')
                    
                    # folder 크기 확인
                    # folder_scale = get_size(_path_) / (1024.0 * 1024.0 * 1000.0)
                    
                    diskInfo  = os.statvfs('/')
                    free      = diskInfo.f_bsize * diskInfo.f_bavail / (1024.0 * 1024.0 * 1000.0)
                    
                    if free > ALLOW_CAPACITY:
                        print(f"After remove file : {free:.2f} GB")
                        break
                    
                    max_day_cnt -= 1
                    
        except Exception as e: # 에러 출력
            print(e) 
    
    if _time.minute == 0 and _time.second < 5 and BOOL_HOUR_CHECK == False:
            
        try: # 이 자리에 시간마다 처리하고 싶은 코드를 집어 넣으면 됨.
            # folder_scale = get_size(_path_) / (1024.0 * 1024.0 * 1000.0)
            _path_ = re.sub("\n", "", _path_)
            diskInfo  = os.statvfs(_path_)
            used      = diskInfo.f_bsize * (diskInfo.f_blocks - diskInfo.f_bavail) / (1024.0 * 1024.0 * 1000.0)
            free      = diskInfo.f_bsize * diskInfo.f_bavail / (1024.0 * 1024.0 * 1000.0)
            total     = diskInfo.f_bsize * diskInfo.f_blocks / (1024.0 * 1024.0 * 1000.0)
            
            print(f"use : {used:.2f} | free : {free:.2f} | total : {total:.2f}")
            os.system(f"echo intflow3121 | sudo -S find {_path_} -name '*.mp4'")
            
            if free < total * ALLOW_CAPACITY_RATE:
                max_day_cnt = 30
                while (max_day_cnt >= -1):
                    
                    # folder 내부 날짜순으로 제거
                    os.system(f"echo intflow3121 | sudo -S find {_path_} -name '*.mp4' -ctime +{max_day_cnt}" + " -exec rm -rf {} \;")
                    os.system(f"echo intflow3121 | sudo -S find {_path_} -name '*.jpeg' -ctime +{max_day_cnt}" + " -exec rm -rf {} \;")
                    os.system(f"echo intflow3121 | sudo -S find {_path_} -name '*.jpg' -ctime +{max_day_cnt}" + " -exec rm -rf {} \;")
                    # command = f"find {_path_} -type f -ctime +{max_day_cnt}" + " -exec rm -rf {} \;"
                    # os.popen("sudo -S %s"%(command), 'w').write('intflow3121')
                    
                    # folder 크기 확인
                    # folder_scale = get_size(_path_) / (1024.0 * 1024.0 * 1000.0)
                    
                    diskInfo  = os.statvfs(_path_)
                    free      = diskInfo.f_bsize * diskInfo.f_bavail / (1024.0 * 1024.0 * 1000.0)
                    
                    if free > total * ALLOW_CAPACITY_RATE:
                        print(f"After remove file : {free:.2f} GB")
                        break
                    
                    max_day_cnt -= 1
                    
        except Exception as e: # 에러 출력
            print(e) 
            
        if BOOL_HOUR_CHECK == False:
            BOOL_HOUR_CHECK = True
    
    elif _time.minute == 0 and _time.second > 5 and BOOL_HOUR_CHECK == True:
        BOOL_HOUR_CHECK = False
        
    return BOOL_HOUR_CHECK

if __name__ == "__main__":

    fan_speed_set(configs.FAN_SPEED)
    port_info_set()
    first_booting=True
    docker_repo = configs.docker_repo
    docker_image_tag_header = configs.docker_image_tag_header  
    # docker_image, docker_image_id = find_lastest_docker_image("intflow/edgefarm:hallway_dev_v")
    docker_image, docker_image_id = find_lastest_docker_image(docker_repo + ":" + docker_image_tag_header)
    


    # socket 서버 시작
    print("\nRUN Socket Server!\n")
    if port_status_check(configs.PORT):
        port_process_kill(configs.PORT)
    if port_status_check(configs.http_server_port):
    	port_process_kill(configs.http_server_port)
    # socket_server_thr = threading.Thread(target=socket_server_run)
    # socket_server_thr.start()
    # socket_server_run()
    
    socket_server_process = multiprocessing.Process(target=socket_server_run)
    socket_server_process.start()
    
    http_server_process = multiprocessing.Process(target=httpserver.run_httpserver)
    http_server_process.start()

    
    # 폴더 자동삭제를 위한 설정
    f = open("/edgefarm_config/Smart_Record.txt","rt")
    _ = f.readline()
    _path_ = f.readline()
    f.close()
    print(f"[Info] target video folder : {_path_}")
    # _path_ = '/edgefarm_config/Recording' # folder path를 변수로 입력
    # ALLOW_CAPACITY = 100 # 단위 : gb, 폴더 허용 최대크기
    ALLOW_CAPACITY_RATE = 0.02 # 단위 : rate, 폴더 저장 MAX percent
    BOOL_HOUR_CHECK = False # 한시간 마다 체크, 시간 상태 처리를 한번만 할 때 유용함
    
    # ! 맨 처음 실행했을 떄 한번 체크하게 설정
    _time = datetime.datetime.now()
    folder_value_check(_time, _path_, ALLOW_CAPACITY_RATE, BOOL_HOUR_CHECK, FIRST_BOOT_REMOVER = True)

    # edgefarm 구동.
    while (True):
        # edgefarm docker 가 켜져있는지 체크
        if check_deepstream_status():
            
            pass
        else:
            # docker 실행과 동시에 edgefarm 실행됨.
            docker_image, docker_image_id = find_lastest_docker_image(docker_repo + ":" + docker_image_tag_header)
            run_docker(docker_image, docker_image_id)
            
            deepstreamCheck_queue = Queue()
            deepstreamCheck_thread_mutex = threading.Lock()
            deepstreamCheck_thread_cd = threading.Condition()
            deepstreamCheck_thread = threading.Thread(target=check_deepstream_exec,args=(first_booting,))
            deepstreamCheck_thread.start()
            first_booting=False
        if port_status_check(configs.http_server_port) == False:
            multiprocessing.Process(target=httpserver.run_httpserver).start()
        if port_status_check(configs.PORT) == False:
            multiprocessing.Process(target=socket_server_run).start()
            
        # 동영상 폴더 제거 알고리즘
        _time = datetime.datetime.now()
        BOOL_HOUR_CHECK = folder_value_check(_time, _path_, ALLOW_CAPACITY_RATE, BOOL_HOUR_CHECK)

        time.sleep(0.5) # 1초 지연.

    socket_server_process.terminate()
    print("socket server process end")

    print("\nEdgefarm End...\n")

