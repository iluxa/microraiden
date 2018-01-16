# Prepare environment
This instruction has been tested on Ubuntu 17.10
Ropsten ethereum network must be synced, two accounts need for test:
<account1> - account 1 ropsten ethereum address
<path_account1_password> - path to file with <account1> password
<account2> - account 2 ropsten ethereum address
- geth command for the test:
geth --testnet --syncmode fast --cache 1024 --rpc --rpcaddr 127.0.0.1 --rpcport 8545 --unlock <account1> --password <path_account1_password> --rpcapi admin,debug,miner,shh,txpool,personal,eth,net,web3

## Enter commands:
```
virtualenv -p python3 env
. env/bin/activate
git clone https://github.com/iluxa/microraiden
cd microraiden/microraiden
pip3 install -r requirements-dev.txt
pip3 install -e .
```

# Build contracts:

```
cd ../contracts
populus compile
```

# Install contracts:

```
python3 -m deploy.deploy_testnet --owner <account1>
```
This coman take about 6 minutes

After contract deployed you should see address of token and channel manager in the message:
```
CustomToken address is <token_address>
RaidenMicroTransferChannels address is <channel_address>
```
you also can explore transactions at address:
https://ropsten.etherscan.io/address/<account1>

## Copy keys <account1> and <account2> keyfiles from geth store to <git_root>/microraiden directory with name respectively key1 and key2
## Create file password.txt with <account1> password in <git_root>/microraiden directory
## Change files permission:
```
cd <git_root>/microraiden
chmod 600 key1 key2 password.txt
```

## Change settings in the file <git_root>/microraiden/microraiden/config.py:
in line
```
'3': NetworkConfig('0x161a0d7726EB8B86EB587d8BD483be1CE87b0609', 2400640),
```
replace address 0x161a0d7726EB8B86EB587d8BD483be1CE87b0609 with <channel_address>
replace start_block 2400640 with value when <channel_address> is created

## Start server with commands in new terminal:
```
cd <git_root>/microraiden
. ../../env/bin/activate
python3 -m microraiden.examples.server --private-key key2
```
Enter <address2> password after it requested

## Start client with commands in new terminal:
```
cd <git_root>/microraiden
. ../../env/bin/activate
python3 -m microraiden.examples.client --private-key key1 --password-path ~/password.txt --reqs 100
```

You can see stats during test in client terminal and explore ropsten.etherscan.io for transacrions
