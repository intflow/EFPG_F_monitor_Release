HOST = ""
PORT = 8101 # default

http_server_host = "0.0.0.0"
http_server_port = 8000 # default

engine_socket_port = 8100 # default

FAN_SPEED = 150

API_HOST = "http://intflowserver2.iptime.org:20052"

# API_HOST2 = "http://intflowserver2.iptime.org:20051"
API_HOST2 = "http://intflowserver2.iptime.org:60080"
METADATA_DIR = "/edgefarm_config/metadata"

docker_repo = "intflow/efpg_f"
docker_image_tag_header = "dev"
local_edgefarm_config_path = "/edgefarm_config"
edgefarm_config_path = "/edgefarm_config/edgefarm_config.json"
edgefarm_port_info_path = "/edgefarm_config/port_info.txt"
container_name = "efhall_test"
roominfo_dir_path = "/edgefarm_config/roominfo"
roiinfo_dir_path = "/edgefarm_config/roiinfo"
recordinginfo_dir_path = "/edgefarm_config/Recording"
DB_datetime=""
MetaDate_path="/edgefarm_config/metadata/"
edgefarm_config_json_path = "/edgefarm_config/edgefarm_config.json"
model_export_container_name = "export_model"
server_bucket_of_model = "intflow-models"
server_model_file_name = "intflow_model.onnx"
local_model_file_relative_path = "model/intflow_model.onnx"
commit_container_name = "for_commit"
deepstream_num_exec="/edgefarm_config/deepstream_num_of_exec.json"
mount=0
mount_server_id="intflow"
mount_server_pw="intflow3121"
mount_server_ip="192.168.0.103"
mount_remote_id="intflow"
mount_remote_pw="intflow3121"
mount_remote_path = "/home/intflow/works/VIDEO/records_win/edgefarm_record"
mount_dir_path = "/edgefarm_config/Recording"
mount_done_flag_file = "mount_key.txt"
firmware_dir = "/home/intflow/works/firmwares/"
key_match_dict = {
    'device_id' : 'id',
    'auto_mode' : 'auto_mode_status',
    'auto_stop_second' : 'auto_interval'
}

server_api_path = "/device/info"
access_api_path = "/device/access"
last_ip = None

engine_socket_port_end = 70
device_socket_port_end = 71
http_server_port_end = 72

docker_id = "kmjeon"
docker_pw = "1011910119a!"

log_save_dir_path_host = "/home/intflow/works/logs/"
log_save_dir_path_docker = "/works/logs/"
log_max_volume = 536870912 # bytes 단위 3달은 버팀.
# log_max_volume = 200000 # bytes 단위 3달은 버팀.


internet_ON = True