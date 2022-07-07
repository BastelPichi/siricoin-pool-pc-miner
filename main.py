import sha3
import time
import json
import requests
import colorama

address = "0x4baE9F81a30b148Eb40044F6268B5496861Cb313"
pool = "http://168.138.151.204/poolsiri/"

def beacon_root(last_block, time_stamp, address):
    messages = sha3.keccak_256(b"null").digest()
    root = sha3.keccak_256(bytes.fromhex(last_block.replace("0x", "")) + int(time_stamp).to_bytes(32, 'big') + messages + bytes.fromhex(address.replace("0x", "")))
    return root.digest()

def formatHashrate(hashrate):
    if hashrate < 1000:
        return f"{round(hashrate, 2)}H/s"
    elif hashrate < 1000000:
        return f"{round(hashrate/1000, 2)}kH/s"
    elif hashrate < 1000000000:
        return f"{round(hashrate/1000000, 2)}MH/s"
    elif hashrate < 1000000000000:
        return f"{round(hashrate/1000000000, 2)}GH/s"

r = requests.post(pool, json={"id": None, "method": "mining.authorize", "params": [address]})

if not r.json()["result"]:
    print("Login failed")
    raise SystemExit

login_id = r.json()["id"]

while True:
    job = requests.post(pool, json={"id": login_id, "method": "mining.subscribe", "params": ["ESP8266"]})

    job = job.json()["params"]

    job_id = job[0]

    last_block = job[1]
    target = job[2]

    nonce = job[3]
    nonce_max = job[4]

    diff = job[6]
    time_stamp = job[7]

    pool_address = job[9]

    root = beacon_root(last_block, time_stamp, pool_address)

    root = sha3.keccak_256(root)

    root.update((0).to_bytes(24, "big"))

    proof = "0x00"
    nonce_final = 0


    start_time = time.time()

    for i in range(nonce, nonce_max):
        hash = root.copy()
        hash.update(i.to_bytes(32, 'big'))
        if (int.from_bytes(hash.digest(), "big") < int(target, 16)):
            print(f"{colorama.Fore.GREEN}Found block, shouldnt have mined on the pool 🙃{colorama.Fore.RESET}")
            proof = "0x" + hash.hexdigest()
            nonce_final = i
            break

    hashrate = (nonce_max - nonce) / (time.time() - start_time)

    print(f"{colorama.Fore.YELLOW}Hashrate:", formatHashrate(hashrate), colorama.Fore.RESET)

    time.sleep(4) # prevent getting banned

    submit = requests.post(pool, json={"id": login_id, "method": "mining.submit", "params": [address, job_id, proof, nonce_final]})

    if submit.json()["result"]:
        if submit.json()["raw"]:
            tx = "TXID: "+ json.loads(submit.json()["raw"])["result"][0]
        else:
            tx = "Pool dry, no payout TXID \:"
        print(submit.json())
        print(f"{colorama.Fore.GREEN}Share accepted. ", tx, colorama.Fore.RESET)
    else:
        print(f"{colorama.Fore.RED}Share rejected.{colorama.Fore.RESET}")
        time.sleep(25) # wait for unban
    
    time.sleep(3) # dont overload pool
