#!/bin/bash

# 1. get the latest graffiti docker image
# could let docker-compose do this, but we want to minimize downtime
echo -e "\n  ---  1/5 Pulling graffiti docker image...\n"
docker pull ramirond/graffiti

# 2. stopping rocketpool
echo -e "\n  ---  2/5 Stopping rocketpool...\n"
rocketpool service stop -y

# (3_pre remove graffiti section if it's present already, we dont need it more than once)
# (this is not nice, but it seems to work; also see https://stackoverflow.com/questions/37680636/sed-multiline-delete-with-pattern)
sed -i '/  graffiti:/{:a;N;/      - eth2/!ba};/  graffiti:/d' ~/.rocketpool/docker-compose.yml

# 3. modify rocketpool's docker stack to start the new container
# Note: This doesn't touch any other config changes that the user might have made (like using a different node db mount location)
echo -e "\n  ---  3/5 Adding graffiti container to rocketpool stack...\n"
sed -i '/services:/a\
  graffiti:\
    image: ramirond/graffiti\
    container_name: ${COMPOSE_PROJECT_NAME}_graffiti\
    restart: unless-stopped\
    volumes:\
      - ./data:/data\
    networks:\
      - net\
    command: "--network pyrmont --client $VALIDATOR_CLIENT --out-file /data/graffiti.txt --eth2-url eth2 --eth2-port 5052"\
    depends_on:\
      - eth2' ~/.rocketpool/docker-compose.yml

# 4. adjust the validator script to load graffiti from file
echo -e "\n  ---  4/5 Instructing validator to load the dynamic graffiti...\n"
# We could just statically replace the entire script as users typically won't modify this
# But it's probably good style to only touch our stuff anyways
sed -i 's/-graffiti "$GRAFFITI"/-graffiti-file \/data\/graffiti.txt/' ~/.rocketpool/chains/eth2/start-validator.sh
# There must be a one-liner to this, but I've no clue what that would look like
sed -i 's/-graffiti="$GRAFFITI"/-graffiti-file=\/data\/graffiti.txt/' ~/.rocketpool/chains/eth2/start-validator.sh

# 5. restart rocketpool
echo -e "\n  ---  5/5 Restarting rocketpool...\n"
rocketpool service start
