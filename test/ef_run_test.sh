#!/bin/bash

container_name="efpg_F"
docker_image="intflow/efpg_f:dev_v1.0.1.4"

docker run -it \
--name=${container_name} \
--net=host \
--privileged \
--ipc=host \
--runtime nvidia \
-v /home/$USER/works:/works \
-w /opt/nvidia/deepstream/deepstream-6.0/sources/apps/sample_apps/ef_custompipline \
${docker_image} bash

