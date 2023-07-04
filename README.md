## git update 06/30
- Modify to check also private docker image
## git update 07/05
- Docker image update remotly
---

sudo visudo
```
intflow ALL=NOPASSWD: ALL
```
# 0 
```
cd /home/intflow/works
git clone  https://github.com/intflow/ef_process_monitor.git
```
# Release Note
1. docker image 를 자동으로 제일 최신버전으로 찾음. <br>
"intflow/edgefarm:hallway_dev_v" 뒤의 버전을 보고 제일 높은 버전을 고름.<br>

## grow version ef_monitor 

- roominfo folder 추가 : vpi, limit_weight, weight 구성 정보를 포함한 json file 8개 (default : 다비육종 8채널)

- ~~아직 for_supervisor에 폴더를 감시해서 지우는 코드 없음.~~

- docker 시작하기 전에 서버와 통신해서 device_info 받아오면 폴더 지우고 재생성 후 json 파일 생성.<br>
device_info 못받아온다면 기존의 json 파일의 cam_id 를 전부 -1로 바꿈.

- mac address 고정값으로 박아져있음. 수정해야함.


---
<br>

# 1. `edgefarm_config` 디렉토리 복사하기
```
sudo cp -r ./edgefarm_config /
```
`edgefarm_config` 디렉토리 채로 최상단 디렉토리(`/`)로 복사.<br><br>
**그리고 권한 바꿔주기**
```
sudo chmod 777 -R /edgefarm_config/
```
<br>

# 1.1 각 엣지 디바이스에 맞는 모델 변경 
```
/edgefarm_config/model/intflow_model.engine # 여기에 edgefarm model 넣어줘야함 
```


# ~~2. `/edgefarm_config/port_info.txt`의 값 바꾸기~~
# 2. 그대로 둬도 상관없음!!!
```
8554
5400
224.224.255.xxx
```
위와 같이 되어있는데 각각 아래와 같은 값을 의미한다.
```
rtsp stream port
UDP port
UDP host
```
~~`UDP port` 가 동일 네트워크의 다른 디바이스와 겹치면 안된다.~~<br>
겹쳐도 상관없도록 해결!<br>
`rtsp stream port` 는 8554<br>
`udp port` 는 5400 그대로 두도록
<br>

# 3. dependency
```
sudo apt install -y python3-pip && \
python3 -m pip install pip && \
python3 -m pip install getmac && \
python3 -m pip install natsort && \
pip3 install GitPython
```
<br>

# 4. docker 권한변경
```
sudo usermod -aG sudo $USER && \
sudo usermod -aG docker $USER && \
sudo chown -R $USER:$USER /home/$USER/.docker
```
로그아웃 후 재로그인 혹은 ssh 다시 접속



# 5. SmartRecord seTTing 
- /edgefarm_config/Smart_Record.txt파일 
```
Smart_Recoding  # 녹화할 영상의 title ex)darvi_hallway 
/edgefarm_config/Recording   # 녹화 동영상 path  , docker에서 돌았을때 저장 될  path로 설정
```
# 5.1 mount 



### mount 할 서버 셋팅 
```
apt-get install nfs-common nfs-kernel-server rpcbind portmap

sudo vi /etc/exports
```

```

/home/intflow/works/VIDEO/records_win/edgefarm_record/{client ip end number ex : 16} 172.31.0.0/16(rw,sync,no_subtree_check)
# /home/intflow/works/VIDEO/records_win/edgefarm_record/16 172.31.0.0/16(rw,sync,no_subtree_check)

```

- 반영
```
sudo mkdir /home/intflow/works/VIDEO/records_win/edgefarm_record/{client ip end number ex : 16}
# sudo mkdir /home/intflow/works/VIDEO/records_win/edgefarm_record/16
exportfs -a
systemctl restart nfs-kernel-server
```
### mount 당할 client 셋팅
```
apt-get install nfs-common
sudo mount 192.168.0.103:/home/intflow/works/VIDEO/records_win/edgefarm_record/{client ip end number ex : 16} /edgefarm_config/Recording
# sudo mount 192.168.0.103:/home/intflow/works/VIDEO/records_win/edgefarm_record/16 /edgefarm_config/Recording
```

### auto mount 수정 
```
sudo vi configs.py

mount=True
mount_remote_path = "192.168.0.103:/home/intflow/works/VIDEO/records_win/edgefarm_record/" #mount 할 path (ip빼고)
mount_dir_path = "/edgefarm_config/Recording" # mount당할 path 
mount_done_flag_file = "mount_key.txt"



mount_server_id=마운트할 서버 아이디 
mount_server_pw="마운트할 서버 비밀번호"
mount_server_ip="마운트할 서버 아이피"
mount_remote_id="마운트한 디바이스 아이디"
mount_remote_pw="마운트한 디바이스 비밀번호"
```
### sshpass install 

```
sudo apt install sshpass
```



# 6 auto runs service 
```
bash autorun_service_registration.sh
bash autorun_service_start.sh
```
```
bash autorun_service_stop.sh
```


# 7 Set the model to load on its own device
##### 각각의 디바이스마다 모델을 다르게 설정하기위해 오버피팅 된 모델을 /edgefarmconfig/model/intflow_model.engine를 셋팅해주면 된다 
