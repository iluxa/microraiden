import time
import sys
import logging
from itertools import count
from typing import List

from eth_utils import is_same_address, encode_hex
from web3 import Web3, HTTPProvider
from web3.contract import Contract

from web3.middleware.pythonic import (
    pythonic_middleware,
    to_hexbytes,
)

from microraiden import Client
from microraiden.client import Channel
from microraiden.utils import get_logs, sign_balance_proof, privkey_to_addr
from microraiden.exceptions import InvalidBalanceProof, NoOpenChannel, InvalidBalanceAmount
from microraiden.test.fixtures.channel_manager import start_channel_manager
from microraiden.channel_manager import ChannelManager
from microraiden.test.config import (
    RECEIVER_ETH_ALLOWANCE,
    RECEIVER_TOKEN_ALLOWANCE
)
import gevent
import pytest
from microraiden.make_helpers import make_channel_manager

log = logging.getLogger(__name__)

#w3 = chain.web3
w3 = Web3(HTTPProvider("http://localhost:8545", request_kwargs={'timeout': 60}))
print('Web3 provider is', w3.providers[0])

# Temporary fix for Rinkeby; PoA adds bytes to extraData, which is not yellow-paper-compliant
# https://github.com/ethereum/web3.py/issues/549
if int(w3.version.network) == 4:
    txn_wait = 500
    size_extraData_for_poa = 200   # can change
        
    pythonic_middleware.__closure__[2].cell_contents['eth_getBlockByNumber'].args[1].args[0]['extraData'] = to_hexbytes(size_extraData_for_poa, variable_length=True)
    pythonic_middleware.__closure__[2].cell_contents['eth_getBlockByHash'].args[1].args[0]['extraData'] = to_hexbytes(size_extraData_for_poa, variable_length=True)


def wait_for_blocks(n):
    while w3.eth.blockNumber < n:
        gevent.sleep();

def open_channel(
        channel_manager: ChannelManager,
        client: Client,
        receiver_address: str,
        ):
    channel = client.open_channel(receiver_address, 10)
    wait_for_blocks(channel_manager.n_confirmations + 1)
    gevent.sleep(channel_manager.blockchain.poll_interval)
    time.sleep(30)
#time.sleep(120)
    print("channels: ", channel_manager.channels)
    print("sender: ", channel.sender)
    print("block: ", channel.block)
#assert (channel.sender, channel.block) in channel_manager.channels

    return channel

def coins(n):
    return n * (10**18)


def test_payment(
        channel_manager: ChannelManager,
        confirmed_open_channel,
        receiver_address: str,
        receiver_privkey: str,
        sender_privkey: str,
        sender_address: str,
        block_num
):
#channel_manager.wait_sync()
#confirmed_open_channel.sender = "0x09226F56C5699E2d87700179507cf25FA2F79F6b"
#confirmed_open_channel.block = 2000508
#channel_id = (confirmed_open_channel.sender, confirmed_open_channel.block)
    channel_id = ('0xA7Ac54048B81041dbD527B603175C17473CE2d95', block_num);
    print("channels: ", channel_manager.channels);
    channel_rec = channel_manager.channels[channel_id]
    print("last_sig: ", channel_rec.last_signature);
    print("old_sig: ", channel_rec.old_signature);
    print("balance: ", channel_rec.balance);
    print("old_balance: ", channel_rec.old_balance);
    print("sender_address: ", sender_address);
    print("receiver_address: ", receiver_address);
    print("contract_address: ", channel_manager.channel_manager_contract.address);

#assert channel_rec.last_signature is None
#assert channel_rec.balance == 0

    # valid transfer
#sig1 = encode_hex(confirmed_open_channel.create_transfer(2))
    sig1 = encode_hex(sign_balance_proof(
        sender_privkey,  # should be sender's privkey
#'0xA7Ac54048B81041dbD527B603175C17473CE2d95',
        '0x09226F56C5699E2d87700179507cf25FA2F79F6b',
        block_num,
#channel_rec.receiver,
#channel_rec.open_block_number,
        coins(2),
        channel_manager.channel_manager_contract.address
    ))
    sig2 = encode_hex(sign_balance_proof(
        sender_privkey,  # should be sender's privkey
        '0x09226F56C5699E2d87700179507cf25FA2F79F6b',
        block_num,
        coins(5),
        channel_manager.channel_manager_contract.address
    ))


    channel_manager.register_payment(sender_address, block_num, coins(2), sig1)

    channel_manager.register_payment(sender_address, block_num, coins(5), sig2)
    channel_manager.unregister_payment(sender_address, block_num)

#channel_manager.register_payment(receiver_address, channel_rec.open_block_number, 2, sig1)
    channel_rec = channel_manager.channels[channel_id]
    print("last_sig2: ", channel_rec.last_signature);
#assert channel_rec.balance == 2
#assert channel_rec.last_signature == sig1
    return

    # transfer signed with wrong private key
    invalid_sig = encode_hex(sign_balance_proof(
        receiver_privkey,  # should be sender's privkey
        channel_rec.receiver,
        channel_rec.open_block_number,
        4,
        channel_manager.channel_manager_contract.address
    ))
    with pytest.raises(InvalidBalanceProof):
        channel_manager.register_payment(sender_address, channel_rec.open_block_number, 4,
                                         invalid_sig)
    channel_rec = channel_manager.channels[channel_id]
    assert channel_rec.balance == 2
    assert channel_rec.last_signature == sig1

    # transfer to different receiver
    invalid_sig = encode_hex(sign_balance_proof(
        sender_privkey,
        sender_address,  # should be receiver's address
        channel_rec.open_block_number,
        4,
        channel_manager.channel_manager_contract.address
    ))
    with pytest.raises(InvalidBalanceProof):
        channel_manager.register_payment(sender_address, channel_rec.open_block_number, 4,
                                         invalid_sig)
    channel_rec = channel_manager.channels[channel_id]
    assert channel_rec.balance == 2
    assert channel_rec.last_signature == sig1

    # transfer negative amount
    invalid_sig = encode_hex(sign_balance_proof(
        sender_privkey,
        receiver_address,
        channel_rec.open_block_number,
        1,  # should be greater than 2
        channel_manager.channel_manager_contract.address
    ))
    with pytest.raises(InvalidBalanceAmount):
        channel_manager.register_payment(sender_address, channel_rec.open_block_number, 1,
                                         invalid_sig)
    channel_rec = channel_manager.channels[channel_id]
    assert channel_rec.balance == 2
    assert channel_rec.last_signature == sig1

    # parameters should match balance proof
    sig2 = encode_hex(confirmed_open_channel.create_transfer(2))
    with pytest.raises(NoOpenChannel):
        channel_manager.register_payment(receiver_address, channel_rec.open_block_number,
                                         4, sig2)
    with pytest.raises(NoOpenChannel):
        channel_manager.register_payment(sender_address, channel_rec.open_block_number + 1,
                                         4, sig2)
    with pytest.raises(InvalidBalanceProof):
        channel_manager.register_payment(sender_address, channel_rec.open_block_number,
                                         5, sig2)
    channel_rec = channel_manager.channels[channel_id]
    assert channel_rec.balance == 2
    assert channel_rec.last_signature == sig1
    channel_manager.register_payment(sender_address, channel_rec.open_block_number, 4, sig2)
    channel_rec = channel_manager.channels[channel_id]
    assert channel_rec.balance == 4
    assert channel_rec.last_signature == sig2

    # should transfer up to deposit
    sig3 = encode_hex(confirmed_open_channel.create_transfer(6))
    channel_manager.register_payment(sender_address, channel_rec.open_block_number, 10, sig3)
    channel_rec = channel_manager.channels[channel_id]
    assert channel_rec.balance == 10
    assert channel_rec.last_signature == sig3

    # transfer too much
    invalid_sig = encode_hex(sign_balance_proof(
        sender_privkey,
        receiver_address,
        channel_rec.open_block_number,
        12,  # should not be greater than 10
        channel_manager.channel_manager_contract.address
    ))
    with pytest.raises(InvalidBalanceProof):
        channel_manager.register_payment(sender_address, channel_rec.open_block_number, 12,
                                         invalid_sig)
    assert channel_rec.balance == 10
    assert channel_rec.last_signature == sig3




receiver_key = '0xdd880da44adb44c91005bc7d51d877627ebfc3a45f67ec7f1be926939af79808'
receiver_address = '0x09226F56C5699E2d87700179507cf25FA2F79F6b'

sender_key = '0x1e8b64bcdbaa6cc995e2f325318ba48d58847e0af229670e0fdbd827033c8de0'
sender_address = '0xA7Ac54048B81041dbD527B603175C17473CE2d95'

#cm_address = '0x45fe9a68af651cc5c0fb2c3afc24bb7205eb7e27'
#cm_address = '0xa18bdF0EdEDc0a43C70D00230AbB691b71D9dcC4'
#cm_address = '0x0f83dc382D4B0880b5e06430F49B0d12dD6fE744'
cm_address = '0xB69c353cbA3be3f33910C7c5fFA54C228bde8934'
#fname = "./test1.data"
#fname = "/home/ilya/.config/microraiden/0x45fe9a68_0x09226F56.db"
fname = "/home/ilya/.config/microraiden/0xB69c353c_0x09226F56.db"
cm = make_channel_manager(receiver_key, cm_address, fname, w3)
#client = Client(receiver_key, receiver_key, cm_address, w3);
client = Client(sender_key, sender_key, cm_address, w3);
#ch = open_channel(cm, client, receiver_address)
#ch = client.get_open_channels(receiver_address);
#ch = client.channels;
ch = cm.channels;
#ch = client.get_suitable_channel(receiver_address, 1);
#ch = client.get_open_channels(sender_address);
print("ch: ", ch)
block_num = 2006163
id = ('0xA7Ac54048B81041dbD527B603175C17473CE2d95', block_num);
ccc = {'sender':'0xA7Ac54048B81041dbD527B603175C17473CE2d95', 'block':block_num}
#print("sender: ", ch[id].sender)
print("sender: ", ch[id])
#print("block: ", ch[id].block)
print("block: ", ch[id])


test_payment(cm, ccc, receiver_address, receiver_key, sender_key, sender_address, block_num)
