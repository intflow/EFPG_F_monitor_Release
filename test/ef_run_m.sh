#!/bin/bash

container_name="test"
docker_image="intflow/efpg_f:dev_v1.0.0.2"

docker run -it \
--name=${container_name} \
--net=host \
--privileged \
--ipc=host \
--runtime nvidia \
-v /edgefarm_config:/edgefarm_config \
-v /home/$USER/works:/works \
-w /opt/nvidia/deepstream/deepstream-6.0/sources/apps/sample_apps/ef_custompipline \
${docker_image} bash

