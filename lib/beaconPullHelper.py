import json

import requests


def getProposalsBeaconchain(network):
    if network == "pyrmont":
        url = "https://pyrmont.beaconcha.in/api/v1/epoch/latest/blocks"
    else:
        url = "https://beaconcha.in/api/v1/epoch/latest/blocks"
    try:
        page = requests.get(url)
    except requests.exceptions.RequestException as e:
        print("can't reach Beaconcha.in: " + e)
        return
    if page.status_code != 200:
        print("status code: " + str(page.status_code))
        return
    p = set()
    for block in page.json()['data']:
        p.add(block['proposer'])
    return p


def getProposalsInfura(network, id, key):
    if network == "pyrmont":
        url = "https://eth2-beacon-pyrmont.infura.io/"
    else:
        url = "https://eth2-beacon-mainnet.infura.io/"
    # 1. get current head
    head = "eth/v1/beacon/headers/head"
    try:
        page = requests.get(url + head, auth=(id, key))
    except requests.exceptions.RequestException as e:
        print("can't reach Infura: " + e)
        return
    if page.status_code != 200:
        print("Infura request error " + str(page.status_code) + ": " + str(page.content))
        return

    next_epoch = int(int(page.json()["data"]["header"]["message"]["slot"]) / 32 + 1)  # Teku / Infura can look 1 epoch ahead!
    # 2. get proposers
    prop = "eth/v1/validator/duties/proposer/" + str(next_epoch)
    try:
        page = requests.get(url + prop, auth=(id, key))
    except requests.exceptions.RequestException as e:
        print("can't reach Infura: " + e)
        return
    if page.status_code != 200:
        print("Infura request error " + str(page.status_code) + ": " + str(page.content))
        return
    # return index or pubkey ?
    p = set()
    for block in page.json()['data']:
        p.add(block['validator_index'])
    return p


# works for all clients which implement the official Beacon Node HTTP-REST API (https://ethereum.github.io/eth2.0-APIs/#)
# currently, that's: infura, teku, lighthouse
def getProposalsTeku(ip, port):
    url = "http://" + ip + ":" + str(port)
    head = "/eth/v1/beacon/headers/head"
    try:
        page = requests.get(url + head)
    except requests.exceptions.RequestException as e:
        print("can't reach Teku")
        return
    if page.status_code != 200:
        print("Teku request error " + str(page.status_code) + ": " + str(page.content))
        return

    next_epoch = int(int(page.json()["data"]["header"]["message"]["slot"]) / 32)
    if True:
        # Teku / Infura can look 1 epoch ahead, lh can't
        next_epoch += 1
    # 2. get proposers
    prop = "/eth/v1/validator/duties/proposer/" + str(next_epoch)
    try:
        page = requests.get(url + prop)
    except requests.exceptions.RequestException as e:
        print("can't reach Teku: " + e)
        return
    if page.status_code != 200:
        print("Teku request error " + str(page.status_code) + ": " + str(page.content))
        return
    # return index or pubkey ?
    p = set()
    for block in page.json()['data']:
        p.add(block['validator_index'])
    return p


def getProposalsPrysm(url, port):

    return


# JSON-RPC istead of HTTP
def getProposalsNimbus(ip, port):
    url = "http://" + ip + ":" + str(port) + "/jsonrpc"

    headers = {'content-type': 'application/json'}

    payload = {
        "method": "getBeaconHead",
        "params": [],
        "jsonrpc": "2.0",
        "id": "id",
    }
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
    except requests.exceptions.RequestException as e:
        return False
    if response.status_code != 200:
        print("Nimbus request error " + str(response.status_code) + ": " + str(response.content))
        return

    next_epoch = int(response.json()["result"] / 32) + 0  # TODO can nimbus look ahead too ?

    payload = {
        "method": "get_v1_validator_duties_proposer",
        "params": [next_epoch],
        "jsonrpc": "2.0",
        "id": "id",
    }
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
    except requests.exceptions.RequestException as e:
        return False
    if response.status_code != 200:
        print("Nimbus request error " + str(response.status_code) + ": " + str(response.content))
        return

    p = set()
    for block in response.json()['result']:
        p.add(block['validator_index'])
    return p
