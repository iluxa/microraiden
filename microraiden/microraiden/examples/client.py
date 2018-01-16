import signal
import sys
import time
import click
import re

from web3 import Web3, HTTPProvider

from microraiden import Session
import logging
import requests
from microraiden.config import CHANNEL_MANAGER_ADDRESS, WEB3_PROVIDER_DEFAULT

@click.command()
@click.option(
    '--private-key',
    required=True,
    help='Path to private key file or a hex-encoded private key.',
    type=click.Path(exists=True, dir_okay=False, resolve_path=True)
)
@click.option(
    '--password-path',
    default=None,
    help='Path to file containing the password for the private key specified.',
    type=click.Path(exists=True, dir_okay=False, resolve_path=True)
)
@click.option('--reqs', required=True, help='Requests number', default = 20)
def main(
        private_key: str,
        password_path: str,
        reqs: int,
):
    web3 = Web3(HTTPProvider(WEB3_PROVIDER_DEFAULT))
    run(private_key, password_path, CHANNEL_MANAGER_ADDRESS[web3.version.network], reqs)

session = None
exiting = False
rqs = 0
def signal_handler(signal, frame):
    print('Interrupted. Exiting. Please wait')
    global exiting
    global session
    if not exiting:
        exiting = True
        if session:
            print(rqs, " requests processed, closing session.");
            session.close()
        sys.exit(0)

def run(
        private_key: str,
        password_path: str,
        channel_manager_address: str = None,
        reqs: int = 20,
        web3: Web3 = None,
        retry_interval: float = 5,
        endpoint_url: str = 'http://localhost:5000'
):
    # Create the client session.
    global session
    session = Session(
        endpoint_url=endpoint_url,
        private_key=private_key,
        key_password_path=password_path,
        channel_manager_address=channel_manager_address,
        web3=web3,
        initial_deposit = lambda price: 10*1000*1000 * price,
        topup_deposit = lambda price: 10*1000*1000 * price,
        close_channel_on_exit = True,
        retry_interval=retry_interval
    )
    resource = "/test/1"
    # Get the resource. If payment is required, client will attempt to create
    # a channel or will use existing one.
    last_time = time.time()
    global rqs
    last_reqs = 0
    for i in range(0,reqs):
        response = session.get('{}/{}'.format(endpoint_url, resource))

        if response.status_code == requests.codes.OK:
            rqs = rqs + 1
            t = time.time()
            if (t - last_time) >= 1:
                print("transaction rate: ", rqs - last_reqs, " req/sec")
                last_time = t
                last_reqs = rqs
            continue;
            if re.match('^text/', response.headers['Content-Type']):
                logging.info(
                    "Got the resource {} type={}:\n{}".format(
                        resource,
                        response.headers.get('Content-Type', '???'),
                        response.text
                    )
                )
            else:
                logging.info(
                    "Got the resource {} type={} (not echoed)".format(
                        resource,
                        response.headers.get('Content-Type', '???')
                    )
                )
        else:
            logging.error(
                "Error getting the resource. Code={} body={}".format(
                    response.status_code,
                    response.text
                )
            )
    print(rqs, " requests processed, closing session.");
    session.close()
    return response


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    logging.basicConfig(level=logging.INFO)
    main()
