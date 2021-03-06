import requests
import json
import time

url = "http://192.168.178.38:9091/jsonrpc"
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
    while (True):
        getProposals(getCurEpoch())
        time.sleep(12)
