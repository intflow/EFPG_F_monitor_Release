from utils import *
import subprocess
import configs
if __name__ == "__main__":
    docker_repo = configs.docker_repo
    docker_image_tag_header = configs.docker_image_tag_header
    docker_image, docker_image_id = find_lastest_docker_image(docker_repo + ":" + docker_image_tag_header)
    last_docker_image_dockerhub, docker_update_history = search_dockerhub_last_docker_image(docker_repo, docker_image_tag_header)
    if docker_image != last_docker_image_dockerhub :
        print("다름")
        # subprocess.run("docker pull {}".format(docker_repo + ":" + last_docker_image_dockerhub), shell=True)
    else : 
        print("같음")