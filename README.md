# Deprecation Notice

🚨 **This repository is deprecated and no longer maintained.** 🚨

This project is no longer actively developed or maintained. We recommend using [allora-offchain-node](https://github.com/allora-network/allora-offchain-node) as a replacement.

## Why is this project deprecated?

The architecture has been improved and simplified, and heads and workers supported by this project are are not compatible. 


## What should you do?

- **Switch to allora-offchain-node**: [allora-offchain-node](https://github.com/allora-network/allora-offchain-node)
- **Read the Docs**: Refer to docs on architecture (and workers specifically) on [Allora Network Docs](https://docs.allora.network/).


Thank you to everyone who contributed to this project.



# Building a Worker Node with the allocmd CLI
![Docker!](https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white)
![Python!](https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue)
![Apache License](https://img.shields.io/badge/Apache%20License-D22128?style=for-the-badge&logo=Apache&logoColor=white)

The `allocmd` is a CLI tool that handles seamless creation of Allora external resources built to integrate with Allora chain. With this tool, you do not need to write the worker or reputer node or even a validator from scratch, the CLI tool will help you bootstrap all the needed components to get resource working.

The following are the list of stuff that can don with this tool at the moment
1. Generating worker node files
2. Genrating reputer node files
3. Generating validator node files
4. Funding of edgenet account addresses

for all the files generation commands, the tool will help in generation of the needed files and their respective docker files and you can spin them up as usual docker containers with docker-compose

## Install `allocmd` CLI

You will begin with installing the tool on your machine. 

```shell
pip install allocmd
```

> you should use version 1.0.0 for Allora Chain v1 and version 2.0.0 for Allora Chain v2. Run `allocmd --help` to get general help or `allocmd [command] --help` to get help relating to a particular command.

## Initializing resources
### Initialize the worker/reputer for development
> Note that all commands here will pass for both worker or reputer node

The next step is initializing the CLI to bootstrap all the needed components to get your worker or reputer running. The following command will handle the initialization process. It will create all the files in the appropriate directories and generate identities for your node to be used for local development.

```shell
allocmd generate worker --name <preffered name> --topic <topic id> --env dev
```

Before running this command you will have to [pick the topic Id ](https://docs.allora.network/devs/existing-topics) you wish to generate inference for after which you can run this command with the topic Id. The command will auto-create some files, the most important of which is the `dev-docker-compose.yaml`file which is an already complete docker-compose that you can run immediately to see your worker/reputer and head nodes running perfectly on your local machine. You can edit the files as you wish. for instance the `main.py` is meant for you to call your inference server, hence you will have to edit the sample code with actual URLs and logic as you prefer.

When you run the docker-compose (`docker-compose -f dev-docker-compose.yaml up --build`), maybe after you have written and tested your logic in `main.py`, you then should be seeing the logs from the nodes, and you should be able to make a request to your head node and see it get a response from the worker/reputer node. Note that in production, you won't be the one to make the inference request, as the Allora chain will do this at the cadence provided by the topic creator.

You can test your node by running the following curl command:

```
curl --location 'http://localhost:6000/api/v1/functions/execute' --header 'Accept: application/json, text/plain, */*' --header 'Content-Type: application/json;charset=UTF-8' --data '{
    "function_id": "bafybeigpiwl3o73zvvl6dxdqu7zqcub5mhg65jiky2xqb4rdhfmikswzqm",
    "method": "allora-inference-function.wasm",
    "parameters": null,
    "topic": "<TOPIC_ID>",
    "config": {
        "env_vars": [
            {                              
                "name": "BLS_REQUEST_PATH",
                "value": "/api"
            },
            {                              
                "name": "ALLORA_ARG_PARAMS",
                "value": "<argument>"
            }
        ],
        "number_of_nodes": -1,
        "timeout" : 2
    }
}' | jq
```

The `<TOPIC_ID>` needs to be [an existing topic on the chain](https://docs.allora.network/devs/existing-topics). The `<argument>` is what the topic is expecting to receive to perform the inference (as an indication to test, you can use the `DefaultArg`  value from the topic on-chain, e.g. for ETH prediction topic, it should be `"ETH"`).

### Initialize the worker/reputer for production

Your worker/reputer node is now ready to be deployed, the `main.py` has been modified, all env variables passed, and the worker/reputer node is running locally and you are now ready to deploy your worker/reputer to run in the production environment. The following command will handle the generation of the `prod-docker-compose.yaml` file which contains all the keys and parameters needed for your worker/reputer to function perfectly in production.

```shell
allocmd generate worker --env prod
```

By running this command, `prod-docker-compose.yaml` will be generated with appropriate keys and parameters. You can now run the docker-compose file or deploy the whole codebase in your preferred cloud instance. At this stage, your worker should be responding to inference request from the Allora Chain.

### Initialize validator production
```shell
allocmd generate validator --name <validator-name> --network <edgenet>
```
The above command can generate validator files and you can then use docker-compose to deploy

### Fund account address
```shell
allocmd fund <address> 
```
The above command takes address and fund the account with Allora Faucet
