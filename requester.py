import requests
import json
import time
from os import walk

#url = "http://192.168.178.38:9091/jsonrpc"
url = "https://eth2-beacon-pyrmont.infura.io/eth/v1/validator/duties/proposer/"
url2 = "https://eth2-beacon-pyrmont.infura.io/eth/v1/beacon/headers"
user = "1pQO0ZiEx0FExWddgBK31GPQykI"
pas = "3f2f041c2c959d8c3551890df3a6c670"
headers = {'content-type': 'application/json'}


def getProposals(epoch):
    payload = {
        "method": "get_v1_validator_duties_proposer",
        "params": [epoch],
        "jsonrpc": "2.0",
        "id": 0,
    }
    response = requests.post(
        url, data=json.dumps(payload), headers=headers).json()

    print(response)
    # print(json.dumps(response, indent=4))


def getCurEpoch():
    payload = {
        "method": "getBeaconHead",
        "params": [],
        "jsonrpc": "2.0",
        "id": 0,
    }
    response = requests.post(
        url, data=json.dumps(payload), headers=headers).json()

    epoch = int(response["result"] / 32)
    print("epoch:" + str(epoch) + " slot: " + str(response["result"]))
    return epoch


if __name__ == "__main__":
    # TODO reload when new validators are added
    _, filenames, _ = next(walk("/home/leret/tmp/vals/validators"))

    while True:
        cur_slot = int(requests.get(url2, auth=(user, pas)).json()["data"][0]["header"]["message"]["slot"])
        next_epoch = int(cur_slot / 32) + 1
        print("slot: " + str(cur_slot) + ", epoch: " + str(next_epoch - 1))
        arr = requests.get(url + str(next_epoch), auth=(user, pas)).json()["data"]
        for duty in arr:
            if duty["pubkey"] in filenames:
                print("BLOCK PROPOSAL: " + duty["pubkey"] + " on slot: " + duty["slot"])
        time.sleep(32 * 12 - 100)
