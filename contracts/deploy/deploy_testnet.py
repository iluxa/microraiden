'''
A simple Python script to deploy contracts and then do a smoke test for them.
'''
import click
import time
from populus import Project
from eth_utils import (
    is_address,
    to_checksum_address,
)
from utils.utils import (
    check_succesful_tx,
    wait,
)

from web3 import Web3, HTTPProvider
from web3.middleware.pythonic import (
    pythonic_middleware,
    to_hexbytes,
)

@click.command()
@click.option(
    '--chain',
    default='kovan',
    help='Chain to deploy on: kovan | ropsten | rinkeby | tester | privtest'
)
@click.option(
    '--owner',
    help='Contracts owner, default: web3.eth.accounts[0]'
)
@click.option(
    '--challenge-period',
    default=500,
    help='Challenge period in number of blocks.'
)
@click.option(
    '--supply',
    default=10000000,
    help='Token contract supply (number of total issued tokens).'
)
@click.option(
    '--token-name',
    default='TestMOS',
    help='Token contract name.'
)
@click.option(
    '--token-decimals',
    default=18,
    help='Token contract number of decimals.'
)
@click.option(
    '--token-symbol',
    default='TMOS',
    help='Token contract symbol.'
)
@click.option(
    '--token-address',
    help='Already deployed token address.'
)
def main(**kwargs):
    project = Project()

    chain_name = kwargs['chain']
    owner = kwargs['owner']
    challenge_period = kwargs['challenge_period']
    supply = kwargs['supply']
    token_name = kwargs['token_name']
    token_decimals = kwargs['token_decimals']
    token_symbol = kwargs['token_symbol']
    token_address = kwargs['token_address']
    supply *= 10**(token_decimals)
    txn_wait = 250

    assert challenge_period >= 500, 'Challenge period should be >= 500 blocks'

    if chain_name == 'rinkeby':
        txn_wait = 500

    print('''Make sure {} chain is running, you can connect to it and it is synced,
          or you'll get timeout'''.format(chain_name))

    with project.get_chain(chain_name) as chain:
        web3 = chain.web3
        print('Web3 provider is', web3.providers[0])

        # Temporary fix for Rinkeby; PoA adds bytes to extraData, which is not yellow-paper-compliant
        # https://github.com/ethereum/web3.py/issues/549
        if int(web3.version.network) == 4:
            txn_wait = 500
            size_extraData_for_poa = 200   # can change
        
            pythonic_middleware.__closure__[2].cell_contents['eth_getBlockByNumber'].args[1].args[0]['extraData'] = to_hexbytes(size_extraData_for_poa, variable_length=True)
            pythonic_middleware.__closure__[2].cell_contents['eth_getBlockByHash'].args[1].args[0]['extraData'] = to_hexbytes(size_extraData_for_poa, variable_length=True)

        owner = owner or web3.eth.accounts[0]
        assert owner and is_address(owner), 'Invalid owner provided.'
        owner = to_checksum_address(owner)
        print('Owner is', owner)
        assert web3.eth.getBalance(owner) > 0, 'Account with insuficient funds.'

        token = chain.provider.get_contract_factory('TestMOS')

        if not token_address:
            txhash = token.deploy(
                args=[supply, token_name, token_symbol, token_decimals],
                transaction={'from': owner}
            )
            time.sleep(180)
            receipt = check_succesful_tx(chain.web3, txhash, txn_wait)
            token_address = receipt['contractAddress']

        assert token_address and is_address(token_address)
        token_address = to_checksum_address(token_address)
        print(token_name, 'address is', token_address)

        microraiden_contract = chain.provider.get_contract_factory('RaidenMicroTransferChannels')
        txhash = microraiden_contract.deploy(
            args=[token_address, challenge_period, []],
            transaction={'from': owner}
        )
        time.sleep(180)
        receipt = check_succesful_tx(chain.web3, txhash, txn_wait)
        microraiden_address = receipt['contractAddress']

        print('RaidenMicroTransferChannels address is', microraiden_address)


if __name__ == '__main__':
    main()
