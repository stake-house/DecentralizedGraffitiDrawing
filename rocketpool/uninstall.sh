#!/bin/bash

# 1. stopping rocketpool
echo -e "\n  ---  1/4 Stopping rocketpool...\n"
rocketpool service stop -y

# 2. use the static graffiti again
echo -e "\n  ---  2/4 Instructing validator to load the default graffiti...\n"
sed -i 's/-graffiti-file \/data\/graffiti.txt/-graffiti "$GRAFFITI"/' ~/.rocketpool/chains/eth2/start-validator.sh
# There must be a one-liner to this, but I've no clue what that would look like
sed -i 's/-graffiti-file=\/data\/graffiti.txt/-graffiti="$GRAFFITI"/' ~/.rocketpool/chains/eth2/start-validator.sh

# 3. remove the graffiti container
# see "3_pre" of installer script
echo -e "\n  ---  3/4 Removing graffiti container from rocketpool stack...\n"
sed -i '/  graffiti:/{:a;N;/      - eth2/!ba};/  graffiti:/d' ~/.rocketpool/docker-compose.yml
docker container rm rocketpool_graffiti > /dev/null 2>&1 # don't show error message if container is not present
rm ~/.rocketpool/data/graffiti.txt -f

# 4. restart rocketpool
echo -e "\n  ---  4/4 Restarting rocketpool...\n"
rocketpool service start
