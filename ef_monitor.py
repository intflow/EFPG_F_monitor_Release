from concurrent.futures import thread
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
import natsort
import configs
from utils import *
from for_supervisor import *
import firmwares_manager
def autorun_service_check():
    res = subprocess.check_output(" sudo -S supervisorctl status edgefarm_monitor", stderr=subprocess.PIPE, shell=True)
    status_res = res.decode().split()[1]

    return status_res

def autorun_service_start():
    subprocess.run(" sudo -S supervisorctl start edgefarm_monitor", shell=True)

def autorun_service_stop():
    subprocess.run(" sudo -S supervisorctl stop edgefarm_monitor", shell=True)

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
                    subprocess.run(" sudo -S reboot", shell=True) # 그 다음에 디바이스 재부팅.
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
                        subprocess.run("sudo -S reboot", shell=True) # 그 다음에 디바이스 재부팅.
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
        print("\n\nError Socket Server closed!\n\n")
    finally:
        # 에러가 발생하면 서버 소켓을 닫는다.
        server_socket.close()


def control_edgefarm_monitor(control_queue, docker_repo, docker_image_tag_header, socket_server_process_list, http_server_process_list, control_thread_cd):
    global last_docker_image_dockerhub, docker_update_history
    # global control_thread_mutex
    wait_pass = True
    not_print = False
    while True:
        # control_thread_mutex.acquire()
        if wait_pass:
            wait_pass = False
        else:
            with control_thread_cd:
                control_thread_cd.wait()
        if not not_print:
            autorun_service_status = autorun_service_check()
            current_running_docker_image = current_running_image(docker_repo + ":" + docker_image_tag_header)
            last_docker_image_local = find_lastest_docker_image(docker_repo + ":" + docker_image_tag_header)[0]
            if autorun_service_status == "RUNNING":
                autorun_service_status = "\033[92mRUNNING\033[0m"
            ef_engine_status = "\033[92mRUNNING\033[0m" if check_deepstream_status() else "STOPPED"
            device_socket_status = "\033[92mRUNNING\033[0m" if port_status_check(configs.PORT) else "STOPPED"
            if len(socket_server_process_list) > 0 and socket_server_process_list[0].is_alive: # 이 파이썬 프로세스에서 실행한 socket server 가 있다면
                device_socket_status = "\033[92mRUNNING\033[0m (Temporary)"
            elif autorun_service_status == "\033[92mRUNNING\033[0m" and port_status_check(configs.PORT): # autorun service가 실행 중이고 port 도 사용 중이라면
                device_socket_status = "\033[92mRUNNING\033[0m (Background)"
            elif autorun_service_status == "STOPPED" and port_status_check(configs.PORT): # autorun service가 실행 중이 아닌데 port 가 사용 중이라면
                device_socket_status = "\033[92mRUNNING\033[0m (Invalid)"
            else:
                device_socket_status = "STOPPED"
                
            http_server_status = "\033[92mRUNNING\033[0m" if port_status_check(configs.http_server_port) else "STOPPED"
            if len(http_server_process_list) > 0 and http_server_process_list[0].is_alive: # 이 파이썬 프로세스에서 실행한 http server 가 있다면
                http_server_status = "\033[92mRUNNING\033[0m (Temporary)"
            elif autorun_service_status == "\033[92mRUNNING\033[0m" and port_status_check(configs.http_server_port): # autorun service가 실행 중이고 port 도 사용 중이라면
                http_server_status = "\033[92mRUNNING\033[0m (Background)"
            elif autorun_service_status == "STOPPED" and port_status_check(configs.http_server_port): # autorun service가 실행 중이 아닌데 port 가 사용 중이라면
                http_server_status = "\033[92mRUNNING\033[0m (Background)"
            else:
                http_server_status = "STOPPED"
            
            with open(configs.deepstream_num_exec, 'r') as f:
                json_data = json.load(f)

            deepstream_smartrecord = json_data['deepstream_smartrecord']
            deepstream_filesink = json_data['deepstream_filesink']
            DB_AWS_insert = json_data['DB_insert']
                         
            SR_status="STOPPED              "+str(deepstream_smartrecord)    
            filesink_status="STOPPED              "+str(deepstream_filesink)      
            aws_status="STOPPED              "+str(DB_AWS_insert)    
            for line in Popen(['ps', 'aux'], shell=False, stdout=PIPE).stdout:
                result = line.decode('utf-8')
                if result.find('deepstream-SR')>1: # deepstream이 ps에 있는지 확인
                    # print("smart record running")
                    SR_status="\033[92mRUNNING\033[0m (Background) "+str(deepstream_smartrecord)    
                if result.find('deepstream-custom-pipeline')>1: # deepstream이 ps에 있는지 확인
                    filesink_status="\033[92mRUNNING\033[0m (Background) "+str(deepstream_filesink)    
                if result.find('aws')>1: # deepstream이 ps에 있는지 확인
                    aws_status="\033[92mRUNNING\033[0m (Background) "+str(DB_AWS_insert)    
            engine_socket_status = "\033[92mRUNNING\033[0m" if port_status_check(configs.engine_socket_port) else "STOPPED"
            print("\n======================================================")
            print("             Edge Farm Engine Monitor")
            print("\n                                              By. Ryu ")
            print("--------------------------------------------------")
            print("\n\033[2mName                  Status               Times\033[0m")
            print("\nSmart Record          {}".format(SR_status))
            print("\nfilesink deepstream   {}".format(filesink_status))
            print("\nDB_AWS_insert         {}".format(aws_status))
            print("\n--------------------------------------------------")
            print("")
            with open('/edgefarm_config/switch_status.txt', 'r') as file:
                content = file.read()
            my_bool = bool(int(content)) # True
            print("video send Mode: \033[92m{}\033[0m\n".format(my_bool) if my_bool else "video send Mode: \033[91m{}\033[0m\n".format(my_bool))
            print("Last inset time        : {}\n".format(configs.DB_datetime))
            # print("Edge Farm Engine Status : {}".format(ef_engine_status))
            print("AutoRun Service Status : {}\n".format(autorun_service_status))
            print("Device Socket Server : {}".format(device_socket_status))
            # print("Engine Socket Server : {}".format(engine_socket_status))
            print("Http Server          : {}".format(http_server_status))
            print("\nDocker repo : {}".format(docker_repo))
            print("Current \033[92mRUNNING\033[0m docker image   : {}".format(current_running_docker_image))
            print("Last docker image (Local)      : {}".format(last_docker_image_local))
            print("Last docker image (Docker hub) : {}".format(last_docker_image_dockerhub))
            if docker_update_history > 0:
                print("\033[36m{} Update(s) available\033[0m".format(docker_update_history))
            elif docker_update_history == 0:
                print("\033[36mThis is the latest version\033[0m")
            print("\n======================================================\n")
            print("Tips.")
            print(" - To change \"\033[92mRUNNING\033[0m (Temporary or Invalid)\" to \"\033[92mRUNNING\033[0m (Background)\", 7.autostop and then 6.autostart")
            print("\n-----------------")
            print("    COMMANDS")
            print("1. start : EFPG_F routine")
            print("2. log : view docker log mode. (since 24 hours) - 작동 X")
            print("3. s3Upload : Click to turn the original recording video on and off to S3.. - ")
            print("4. dockerstart : docker start- 작동 X 1 로 시랭해" )
            print("5. kill : docker kill")
            print("6. SmartRecord : Start SmartRecord")
            print("7. filesink : Start filesink")
            print("8. exec num clear  : docker restart and deepstream exec num clear")
            print("9. none : none")
            print("10. autostart : Start Auto Run Service")
            print("11. autostop : Stop Auto Run Service")
            # print("10. images : show \"{}\" docker images".format(docker_repo + ":" + docker_image_tag_header))
            # print("11. updatecheck : Check Last docker image from docker hub")
            print("12. send : Send video to aws server & DB ")
            print("13. end : Close Edge Farm Engine Monitor")
            # print("14. database : inset database")
            print("16. export : ")
            print("-----------------\n")
        # control_thread_mutex.release()
        not_print = False
        # print(f"\n\n\n not print : {not_print}\n\n\n")
        user_command = input()
        # print(f"\n\n\n user cm : {user_command}")
        if control_queue.empty():
            if user_command in ["start", "1"]:
                control_queue.put(1)
            elif user_command in ["log", "2"]:
                control_queue.put(2)
                not_print = True
            elif user_command in ["s3Upload", "3"]:
                control_queue.put(3)
            elif user_command in ["dockerstart", "4"]:
                control_queue.put(4)
            elif user_command in ["kill docker", "5"]:
                control_queue.put(5)
            elif user_command in ["SmartRecord ", "6"]:
                control_queue.put(6)
            elif user_command in ["filesink", "7"]:
                control_queue.put(7)
            elif user_command in ["killSmartRecord", "8"]:
                control_queue.put(8)
            elif user_command in ["killfilesink", "9"]:
                control_queue.put(9)
            elif user_command in ["autostart", "10"]:
                control_queue.put(10)
            elif user_command in ["autostop", "11"]:
                control_queue.put(11)
            elif user_command in ["aws", "12"]:
                control_queue.put(12)
            elif user_command in ["database", "14"]:
                control_queue.put(14)
            elif user_command in ["export", "16"]:
                control_queue.put(16)
            elif user_command in ["end", "13"]:
                control_queue.put(13)
                break
            elif user_command == "test":
                control_queue.put(99)
            else:
                wait_pass = True

def print_with_lock(content):
    # global control_thread_mutex
    # control_thread_mutex.acquire()
    global control_thread_cd
    with control_thread_cd:
        print(content)
        control_thread_cd.notifyAll()
    # control_thread_mutex.release()

def docker_log_process_kill(docker_log_process_list):
    if docker_log_process_list[0].is_alive():
        docker_log_end_print()
    docker_log_process_list[0].terminate() # 확인사살
    # docker_log_process_list[0].close() # 자원 해제 . 3.7부터 추가된대
    del(docker_log_process_list[0]) # 리스트에서 없애기

def docker_log_process_start(docker_log_process_list):
    # 새로운 process 시작.
    # control_thread_mutex.acquire()
    # control_thread_mutex.release()
    global control_thread_cd 
    with control_thread_cd:
        print("\n===========================================")
        print("       View docker log mode")
        print("===========================================\n")
        control_thread_cd.notifyAll()
    docker_log_process_list.append(multiprocessing.Process(target=docker_log_view))
    docker_log_process_list[0].start()
    
def socket_server_process_kill(socket_server_process_list):
    print("\nkill socket server")
    socket_server_process_list[0].terminate() # 확인사살
    del(socket_server_process_list[0]) # 리스트에서 없애기
    
def socket_server_process_start(socket_server_process_list):
    if len(socket_server_process_list) > 0: socket_server_process_kill(socket_server_process_list) # 죽어있는 socket server process 가 있다면 삭제
    socket_server_process_list.append(multiprocessing.Process(target=socket_server_run))
    socket_server_process_list[0].start()
    print("\nRUN Socket Server!\n")
    
def http_server_process_kill(http_server_process_list):
    print("\nkill http server")
    http_server_process_list[0].terminate() # 확인사살
    del(http_server_process_list[0]) # 리스트에서 없애기
    
def http_server_process_start(http_server_process_list):
    if len(http_server_process_list) > 0: http_server_process_kill(http_server_process_list) # 죽어있는 http server process 가 있다면 삭제
    http_server_process_list.append(multiprocessing.Process(target=httpserver.run_httpserver))
    http_server_process_list[0].start()
    print("\nRUN http server!\n")


if __name__ == "__main__":
    fan_speed_set(configs.FAN_SPEED)
    port_info_set()
    first_booting=True
    # docker_image_head = "intflow/edgefarm:hallway_dev"
    docker_repo = configs.docker_repo
    docker_image_tag_header = configs.docker_image_tag_header
    docker_image, docker_image_id = find_lastest_docker_image(docker_repo + ":" + docker_image_tag_header)
    
    last_docker_image_dockerhub = "None"
    docker_update_history = -1

    # # socket 서버 시작
    # print("\nRUN Socket Server!\n")
    # socket_server_process = multiprocessing.Process(target=socket_server_run)
    # socket_server_process.start()
    
    socket_server_process_list = []
    http_server_process_list = []
    docker_log_process_list = []

    # control thread 실행
    control_queue = Queue()
    control_thread_mutex = threading.Lock()
    control_thread_cd = threading.Condition()
    control_thread = threading.Thread(target=control_edgefarm_monitor, args=(control_queue, docker_repo, docker_image_tag_header, socket_server_process_list, http_server_process_list, control_thread_cd,))
    control_thread.start()

    docker_log_queue = Queue()


    # edgefarm 구동.
    while (True):
        # edgefarm docker 가 켜져있는지 체크
        # if check_deepstream_status():
        # print("control_queue.empty() : {}".format(control_queue.empty()))
        # 명령 queue 에 값이 들어오면.
        if not control_queue.empty():
            user_command = control_queue.get()
            # print(f"\ncontrol queue get => {user_command}\n")
            if user_command == 1:
                # docker 실행과 동시에 edgefarm engine 실행됨.
                with control_thread_cd:
                    if (check_deepstream_status()):
                        print_with_lock("\nEdge Farm is Already Running\n")
                        print("\nKill docker !")
                        rm_docker()
                    # clear_deepstream_exec()
                    run_docker(docker_image, docker_image_id) # docker 실행
                    docker_image, docker_image_id = find_lastest_docker_image(docker_repo + ":" + docker_image_tag_header)
                    deepstreamCheck_queue = Queue()
                    deepstreamCheck_thread_mutex = threading.Lock()
                    deepstreamCheck_thread_cd = threading.Condition()
                    deepstreamCheck_thread = threading.Thread(target=check_deepstream_exec,args=(first_booting,))
                    deepstreamCheck_thread.start()
                    first_booting=False
                    control_thread_cd.notifyAll()
            elif user_command == 5: # edgefarm end. autorun sevice 도 종료.
                if (check_deepstream_status()): # engine 켜져있다면
                    print("\nKill Edgefarm!")
                    with control_thread_cd:
                        rm_docker() # engine 킬. autorun 이 꺼졌으므로 재시작하지 않음.
                        control_thread_cd.notifyAll()                    
                else:
                    print_with_lock("\nEdge Farm is not Running\n")
            elif user_command == 2: # docker log 보기
                if check_deepstream_status():
                    if len(docker_log_process_list) > 0:
                        if docker_log_process_list[0].is_alive(): # process 가 살아있다면 pass
                            print_with_lock("\nAlready Running View docker log mode...\n")
                        else: # 죽어있다면
                            docker_log_process_kill(docker_log_process_list) # 확인사살하고
                            docker_log_process_start(docker_log_process_list) # 시작

                    else: # list 개수가 0이라면
                        # 새로운 process 시작.
                        docker_log_process_start(docker_log_process_list) # 시작
                else:
                    print_with_lock("\nEdge Farm is not Running\n")
            elif user_command == 3: # 
                with control_thread_cd:
                    with open('/edgefarm_config/switch_status.txt', 'r') as file:
                        content = file.read()
                    my_bool = bool(int(content)) # True
                    my_bool = not my_bool
                    content = str(int(my_bool))
                    # 파일 쓰기
                    with open('/edgefarm_config/switch_status.txt', 'w') as file:
                        file.write(content)
                    control_thread_cd.notifyAll()
            elif user_command == 6: # supervisor start
                # kill_edgefarm()
                with control_thread_cd:
                    print('start Smart Record')
                    # subprocess.run(f"docker exec -dit {configs.container_name} bash ./run_SR.sh", shell=True)
                    run_SR_docker()
                    control_thread_cd.notifyAll()
            elif user_command == 7: # supervisor stop
                with control_thread_cd:
                    print('start filesink')
                    bool_SR_file=False
                    for file in os.listdir(configs.recordinginfo_dir_path):
                        if "SR" in file:
                            bool_SR_file=True
                            break
                    if bool_SR_file:
                        run_file_deepstream_docker()
                    # subprocess.run(f"docker exec -dit {configs.container_name} bash ./run_filesink.sh", shell=True)
                    control_thread_cd.notifyAll()
            elif user_command == 8: # device socket server run
                with control_thread_cd:
                    print('kill Smart Record')
                    subprocess.run(f"docker restart {configs.container_name} ", shell=True)
                    with open(configs.deepstream_num_exec, 'r') as f:

                        json_data = json.load(f)
                    json_data['deepstream_filesink']=0
                    json_data['deepstream_smartrecord']=0
                    json_data['DB_insert']=0
                    with open(configs.deepstream_num_exec, 'w') as f:
                        json.dump(json_data, f)
                    control_thread_cd.notifyAll()
            elif user_command == 9: # device socket server stop
                with control_thread_cd:
                    print('kill filesink')
                    # subprocess.run(f"docker exec -dit {configs.container_name} bash ./kill_filesink.sh", shell=True)                    
                    control_thread_cd.notifyAll()
            elif user_command == 10: # supervisor start
                # kill_edgefarm()
                with control_thread_cd:
                    if autorun_service_check() == "RUNNING":
                        print("\nAuto Run Service is Already Running\n")
                    else:
                        if len(socket_server_process_list) > 0:
                            socket_server_process_kill(socket_server_process_list) # 이 파이썬 프로세스에서 실행한 socket server 프로세스가 있다면 죽임.
                        if port_status_check(configs.PORT): # 종료되지 않은 socket server process 가 있다면
                            print("\nkill socket server")
                            port_process_kill(configs.PORT) # 죽임.
                            
                        if len(http_server_process_list) > 0:
                            http_server_process_kill(http_server_process_list) # 이 파이썬 프로세스에서 실행한 http server 프로세스가 있다면 죽임.
                        if port_status_check(configs.http_server_port): # 종료되지 않은 http server process 가 있다면
                            print("\nkill http server")
                            port_process_kill(configs.http_server_port) # 죽임.
                        # print("port status : {}".format(port_status_check(configs.PORT)))
                        autorun_service_start() # autorun service 시작
                    control_thread_cd.notifyAll()
            elif user_command == 11: # supervisor stop
                with control_thread_cd:
                    if autorun_service_check() == "STOPPED":
                        print("\nAuto Run Service is not Running\n")
                    else:
                        autorun_service_stop() # autorun service 멈춤
                        print("\nkill socket server")
                        port_process_kill(configs.PORT) # socket server port 점유하고 있는 process kill. autorun 파이썬을 종료할 때 port 를 계속 점유하고 있는 경우를 대처하기 위함.
                        print("\nkill http server")
                        port_process_kill(configs.http_server_port) # 죽임.
                    control_thread_cd.notifyAll()
            elif user_command == 12: # send
                with control_thread_cd:
                    print('[SEND video to  aws server] ')
                    # metadataJson = os.listdir(configs.MetaDate_path)
                    # for Json1 in metadataJson:
                    #     with open(configs.MetaDate_path+Json1, 'r') as f:
                    #         json_data = json.load(f)
                    #         if not json_data["updated"]:
                    #             json_data["updated"]=not json_data["updated"]
                    #             with open(configs.MetaDate_path+Json1, 'w') as f:
                    #                 print(json_data)
                    #                 json.dump(json_data, f)
                    metadata_send_ready()
                    metadata_send_res = metadata_send()
                    if True in metadata_send_res:
                        python_log("Database insert successful")
                    else:
                        python_log("Database insert Failed")
                    matching_cameraId_ch2()
                    with open(configs.deepstream_num_exec, 'r') as f:

                        json_data = json.load(f)
                    json_data['DB_insert']=json_data['DB_insert']+1
                    with open(configs.deepstream_num_exec, 'w') as f:
                        json.dump(json_data, f)
                    control_thread_cd.notifyAll()      
            elif user_command == 14: # send
                with control_thread_cd:
                    print('[metadata send] ')
                    metadata_send()
                    control_thread_cd.notifyAll()                                    
            elif user_command == 95: # show docker image list
                with control_thread_cd:
                    show_docker_images_list(docker_repo + ":" + docker_image_tag_header) # 연관된 docker images list 출력
                    control_thread_cd.notifyAll()
            elif user_command == 96: # end
                with control_thread_cd:
                    print("\nCheck update\n")
                    last_docker_image_dockerhub, docker_update_history = search_dockerhub_last_docker_image(docker_repo, docker_image_tag_header)
                    control_thread_cd.notifyAll()
            elif user_command == 97:
                with control_thread_cd:
                    if last_docker_image_dockerhub != "None" and docker_update_history > 0:
                        # subprocess.run("docker pull {}".format(docker_repo + ":" + last_docker_image_dockerhub), shell=True)
                        docker_pull(docker_repo, last_docker_image_dockerhub)
                    elif docker_update_history == 0:
                        print("\nAlready lastest version!\n")
                    else:
                        print("\nPlease updatecheck!\n")
                    control_thread_cd.notifyAll()
            elif user_command == 98: # check edgefram
                with control_thread_cd:
                    check_deepstream_exec()
                    control_thread_cd.notifyAll()
            elif user_command == 13: # end
                break
            elif user_command == 99:
                print_with_lock("\n\ntest success!\n\n")

        # else:
        #     # docker 실행과 동시에 edgefarm 실행됨.
        #     run_docker(docker_image)

        time.sleep(0.5) # 1초 지연.

    if len(docker_log_process_list) > 0 and docker_log_process_list[0].is_alive(): docker_log_process_kill(docker_log_process_list)
    control_thread.join()
    # print("docker control thread end")
    if len(socket_server_process_list) > 0 and socket_server_process_list[0].is_alive(): socket_server_process_kill(socket_server_process_list)
    # print("socket server process end")
    if len(http_server_process_list) > 0 and http_server_process_list[0].is_alive(): http_server_process_kill(http_server_process_list)
    # print("http server process end")

    print("\nEdge Farm Monitor End\n")

