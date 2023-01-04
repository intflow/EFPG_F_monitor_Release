#!/bin/bash

<<<<<<< HEAD
container_name="testcc"
docker_image="intflow/efpg_f:dev_v1.0.1.1"
=======
container_name="DS51"
docker_image="nvcr.io/nvidia/deepstream-l4t:5.1-21.02-samples"
>>>>>>> 898d1d7fe8139a68a272a982aee0d519a207978c

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

