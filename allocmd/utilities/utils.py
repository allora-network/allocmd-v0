import os
import click
import subprocess
from jinja2 import Environment
from importlib.resources import files
from termcolor import colored, cprint
import time
import shutil 
from .typings import Command, BlocklessNodeType
import re
import yaml

def create_worker_account(worker_name, faucet_url, type, network="edgenet"):
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    cli_tool_dir = os.path.dirname(current_file_dir)
    allora_chain_dir = os.path.join(cli_tool_dir, 'allora-chain')

    if not os.path.exists(allora_chain_dir):
        print(colored("Could not find allora-chain. Initializing allora-chain...", "yellow"))
        subprocess.run(
            ['git', 'clone', 'https://github.com/allora-network/allora-chain.git', allora_chain_dir], 
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    else:
        print(colored("Found allora-chain. Pulling latest changes...", "green"))
        subprocess.run(
            ['git', '-C', allora_chain_dir, 'pull', 'origin', 'main'], 
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    
    make_path = shutil.which('make')
    if make_path:
        gopath_output = subprocess.run(['go', 'env', 'GOPATH'], capture_output=True, text=True, check=True)
        gopath = gopath_output.stdout.strip()
        new_path = os.environ['PATH'] + os.pathsep + os.path.join(gopath, 'bin')
        env = os.environ.copy()
        env['PATH'] = new_path
        print(f"allora-chain directory: {allora_chain_dir}")
        subprocess.run(['make', 'install'], 
                        cwd=allora_chain_dir, 
                        check=True)

        key_path = os.path.join(os.getcwd(), f'{worker_name}.{type}.key')
        with open(key_path, 'w') as file:
            subprocess.run(['allorad', 'keys', 'add', worker_name, '--keyring-backend', 'test'], 
                            cwd=allora_chain_dir,
                            env=env, 
                            stdout=file, 
                            stderr=subprocess.STDOUT, 
                            check=True)

        with open(key_path, 'r') as file:
            content = file.read()
            lines = content.splitlines()

        address = re.search(r'address: (\w+)', content).group(1)
        mnemonic = lines[-1].strip()

        process = subprocess.Popen(['allorad', 'keys', 'export', worker_name, '--unarmored-hex', '--unsafe'], 
                                   stdin=subprocess.PIPE, 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE, 
                                   text=True, 
                                   cwd=allora_chain_dir, 
                                   env=env)
        hex_pk_result, errors = process.communicate(input='y\n')
        
        hex_coded_pk = hex_pk_result.strip()
        with open(key_path, "a") as file:
            file.write(f"\nHEX-CODED PRIVATE KEY: \n{hex_coded_pk}")

        subprocess.run([
                        'curl',
                        '-L',
                        f'{faucet_url}send/{network}/{address}'
                    ], stdout=subprocess.DEVNULL)
        
        print(colored(f"keys created and {network}-funded for this {type}. please check config.yaml for your address and mnemonic", "green"))
        return mnemonic, hex_coded_pk, address
    else:
        print(colored("'make' is not available in the system's PATH. Please install it or check your PATH settings.", "red"))
        return ''

def fetch_content_with_curl(url):
    try:
        result = subprocess.run(['curl', '-s', url], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode == 0:
            return result.stdout
        else:
            click.echo(f"Unable to fetch content: {result.stderr}", err=True)
    except Exception as e:
        click.echo(f"Error fetching content: {e}", err=True)

def fundAddress(faucet_url, address, network):
    try:
        subprocess.run([
                        'curl',
                        '-L',
                        f'{faucet_url}send/{network}/{address}'
                    ], stdout=subprocess.DEVNULL)
        
        print(colored(f"address funded with {network}-faucet", "green"))
        return address
    except subprocess.CalledProcessError as e:
        click.echo(f"error funding address: {e}", err=True)

def print_allora_banner():
    """Prints an ASCII art styled banner for ALLORA."""
    banner_text = r"""
    
      __      ___      ___        ______     _______        __      
     /""\    |"  |    |"  |      /    " \   /"      \      /""\     
    /    \   ||  |    ||  |     // ____  \ |:        |    /    \    
   /' /\  \  |:  |    |:  |    /  /    ) :)|_____/   )   /' /\  \   
  //  __'  \  \  |___  \  |___(: (____/ //  //      /   //  __'  \  
 /   /  \\  \( \_|:  \( \_|:  \\        /  |:  __   \  /   /  \\  \ 
(___/    \___)\_______)\_______)\"_____/   |__|  \___)(___/    \___)
                                                                    

    """
    cprint(banner_text, 'blue', attrs=['bold'])

def generate_all_files(env: Environment, file_configs, command: Command, type, name = ''):
    if command == Command.INIT:
        cprint(f"Bootstraping '{name}' directory...", 'cyan')
        time.sleep(1) 

    for config in file_configs:
        template = env.get_template(config["template_name"])

        if command == Command.INIT:
            file_path = os.path.join(os.getcwd(), f'{name}/{type}/{config["file_name"]}')
        elif command == Command.DEPLOY: 
            file_path = os.path.join(os.getcwd(), f'{config["file_name"]}')

        content = template.render(**config["context"])
        with open(file_path, 'w') as f:
            f.write(content)

    if command == Command.INIT:
        cprint("\nAll files bootstrapped successfully. ALLORA!!!", 'green', attrs=['bold'])

def run_key_generate_command(worker_name, type):
    command = (
        f'docker run -it --entrypoint=bash -v "$(pwd)/{worker_name}/{type}/data":/data '
        'alloranetwork/allora-inference-base:latest '
        f'-c "mkdir -p /data/head/key /data/{type}/key && (cd /data/head/key && allora-keys) && (cd /data/{type}/key && allora-keys)"'
    )
    try:
        subprocess.run(command, shell=True, check=True)
        peer_id_path = os.path.join(os.getcwd(), f'{worker_name}/{type}/data/head/key', 'identity')
        with open(peer_id_path, 'r') as file:
            cprint(f"local {type} identity generated successfully.", 'cyan')
            head_peer_id = file.read().strip()
            return head_peer_id
    except subprocess.CalledProcessError as e:
        click.echo(f"error generating local {type} identity: {e}", err=True)

def generateWorkerAccount(worker_name, type):
    config_path = os.path.join(os.getcwd(), worker_name, type, 'config.yaml')
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
    except yaml.YAMLError as e:
        print(colored(f"Error reading config file: {e}", 'red', attrs=['bold']))
        return

    worker_name = config['name']
    faucet_url = config['faucet_url']
    account_details = None
    if not config[type]['mnemonic'] or not config[type]['hex_coded_pk'] or not config[type]['address']:
        account_details = create_worker_account(worker_name, faucet_url, type)

    mnemonic = account_details[0] if account_details else config[type]['mnemonic']
    hex_coded_pk = account_details[1] if account_details else config[type]['hex_coded_pk']
    address = account_details[2] if account_details else config[type]['address']

    if not config[type]['mnemonic'] or not config[type]['hex_coded_pk'] or not config[type]['address']:
        config[type]['mnemonic'] = mnemonic
        config[type]['hex_coded_pk'] = hex_coded_pk
        config[type]['address'] = address
        with open(config_path, 'w') as file:
            yaml.safe_dump(config, file)

    return address

def get_public_ip():
    try:
        result = subprocess.run(['curl', '-4', '-s', 'http://icanhazip.com'], capture_output=True, text=True, check=True)
        public_ip = result.stdout.strip()
        return public_ip
    except subprocess.CalledProcessError as e:
        click.echo(f"error getting public IP: {e}", err=True)
        return None

def generateProdCompose(env: Environment, type, network):
    """Deploy resource production kubernetes cluster"""

    cprint(f"\nMake sure you are running this command in the appropriate directory [validator, reputer, worker]", 'cyan')
    cprint(f"\nif not, please cd to the right directory", 'cyan')
    if click.confirm(colored("\nif you are in the right folder, please proceed", 'white', attrs=['bold']), default=True):

        subprocess.run("mkdir -p ./data/scripts", shell=True, check=True)

        try:
            result = subprocess.run("chmod -R +rx ./data/scripts", shell=True, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"Command '{e.cmd}' returned non-zero exit status {e.returncode}.")
            if e.stderr:
                print(f"Stderr: {e.stderr}")

        config_path = os.path.join(os.getcwd(), 'config.yaml')
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
        except yaml.YAMLError as e:
            print(colored(f"Error reading config file: {e}", 'red', attrs=['bold']))
            return

        worker_name = config['name']
        faucet_url = config['faucet_url']
        hex_coded_pk = config[type]['hex_coded_pk']
        boot_nodes = config[type]['allora_heads'] # concatenate the created head nodes to this as well
        allora_rpc_address = config[type]['allora_rpc_address']
        chain_topic_id = config[type]['topic_id']
        account_address = config[type]['address']

        node_ip = get_public_ip()

        alloraTopic = None
        if type == 'worker':
            alloraTopic = f"allora-topic-{chain_topic_id}-worker"
        elif type == 'reputer':
            alloraTopic = f"allora-topic-{chain_topic_id}-reputer"

        file_configs = [
            {
                "template_name": "prod-docker-compose.yaml.j2",
                "file_name": "prod-docker-compose.yaml",
                "context": {
                    "worker_name": worker_name, 
                    "boot_nodes": boot_nodes, 
                    "allora_rpc_address": allora_rpc_address, 
                    "allora_topic_id": alloraTopic, 
                    "topic_id": chain_topic_id, 
                    "node_ip": node_ip
                }
            },
            {
                "template_name": "init.sh.j2",
                "file_name": "data/scripts/init.sh",
                "context": {
                    "worker_name": worker_name, 
                    "hex_coded_pk": hex_coded_pk
                }
            },
            {
                "template_name": "update-node-ip.sh.j2",
                "file_name": "update-node-ip.sh",
                "context": {}
            }
        ]

        generate_all_files(env, file_configs, Command.DEPLOY, type)

        fundAddress(faucet_url, account_address, network)
        cprint(f"production docker compose file generated to be deployed", 'green')
        cprint(f"please run chmod -R +rx ./data/scripts to grant script access to the image", 'yellow')
        cprint(f"also run chmod +x ./update-node-ip.sh to make update-node-ip.sh execuatable", 'yellow')
    else:
        cprint("\nOperation cancelled.", 'red')


def blocklessNode(environment, env, type, chain_network, name=None, topic=None):
    """Initialize your Allora Worker Node with necessary boilerplates"""

    if not check_docker_running():
        cprint("Docker is not running on your machine, please start docker before running this command", 'red')
        return

    heads_url = f"https://raw.githubusercontent.com/allora-network/networks/main/{chain_network}/heads.txt"
    allora_heads = fetch_content_with_curl(heads_url)

    if chain_network == 'allora-testnet-1':
        faucet_url = 'https://faucet.testnet-1.testnet.allora.network/'
        network = 'testnet-1'
        allora_rpc_address = "https://allora-rpc.testnet-1.testnet.allora.network/"
        allora_api_address = "https://allora-api.testnet-1.testnet.allora.network/"
    elif chain_network == 'edgenet':
        faucet_url = 'https://faucet.edgenet.allora.network/'
        network = 'edgenet'
        allora_rpc_address = "https://allora-rpc.testnet-1.testnet.allora.network/"
        allora_api_address = "https://allora-api.edgenet.allora.network/"
    
    if environment == 'dev':
        if topic is None:
            cprint(f"You must provide topic id when generating {type} in development", 'red')
            return
        elif name is None:
            cprint(f"You must provide name when generating {type} in development", 'red')
            return
        
        alloraTopic = None
        if type == 'worker':
            alloraTopic = f"allora-topic-{topic}-worker"
        elif type == 'reputer':
            alloraTopic = f"allora-topic-{topic}-reputer"

        print_allora_banner()
        cprint("Welcome to the Allora CLI!", 'green', attrs=['bold'])
        print(colored(f"Allora CLI assists in the seamless creation and deployment of Allora {type} nodes", 'yellow'))
        cprint(f"\nThis command will generate some files in the directory named '{name}'.", 'cyan')
        
        if click.confirm(colored("\nWould you like to proceed?", 'white', attrs=['bold']), default=True):
            cprint(f"\nProceeding with the creation of {type} node directory...", 'green')

            head_peer_id = run_key_generate_command(name, type)

            node_ip = get_public_ip()

            file_configs = [
                {
                    "template_name": "Dockerfile.j2",
                    "file_name": "Dockerfile",
                    "context": {}
                },
                {
                    "template_name": "main.py.j2",
                    "file_name": "main.py",
                    "context": {}
                },
                {
                    "template_name": "dev-docker-compose.yaml.j2",
                    "file_name": "dev-docker-compose.yaml",
                    "context": {"head_peer_id": head_peer_id, "allora_topic_id": alloraTopic, "b7s_type": type}
                },
                {
                    "template_name": "requirements.txt.j2",
                    "file_name": "requirements.txt",
                    "context": {}
                },
                {
                    "template_name": "gitignore.j2",
                    "file_name": ".gitignore",
                    "context": {}
                },
                {
                    "template_name": "env.j2",
                    "file_name": ".env",
                    "context": {}
                },
                {
                    "template_name": "config.yaml.j2",
                    "file_name": "config.yaml",
                    "context": {"name": name, "topic_id": topic, "b7s_type": type, "network": chain_network, "faucet_url": faucet_url, "allora_heads": allora_heads, "allora_rpc_address": allora_rpc_address, "allora_api_address": allora_api_address, "node_ip": node_ip}
                }
            ]

            generate_all_files(env, file_configs, Command.INIT, type, name)

            address = generateWorkerAccount(name, type)

            fundAddress(faucet_url, address, chain_network)
        else:
            cprint("\nOperation cancelled.", 'red')
    elif environment == 'prod':
        devComposePath = os.path.join(os.getcwd(), 'dev-docker-compose.yaml')
        if not os.path.exists(devComposePath):
            cprint(f"You must initialize the {type} on dev please run allocmd generate {type} --env dev --name <{type} name> --topic <topic id> --network <{chain_network}> and then run the prod generate in the directory created", 'red')
        else:
            generateProdCompose(env, type, chain_network)










def deployWorker(env: Environment):
    """Deploy resource production kubernetes cluster"""

    print(colored('\nREQUIREMENTS', 'yellow', attrs=['bold']))
    print(colored('1. Ensure to have the Dockerfile built and docker image pushed to your preferred registry.\n'
                  '   You should have your image URI and tag available\n', 'yellow'))
    print(colored('2. Ensure you have your Kubernetes cluster configured to your kubeconfig as the current context.', 'yellow'))
    print(colored('3. Ensure you have updated the ./config.yaml file with image uri and topic id\n'
                  '   Your wallet will be created for you and your mnemonic will be updated automagically\n', 'yellow'))
    

    print(colored('\nDEPENDENCIES', 'yellow', attrs=['bold']))
    print(colored('You must have the following tools installed in your machine to ensure successful deployment\n'
                  '1. helm: for deployment of worker into kubernetes cluster.\n'
                  '2. make: for installation of allora-chain to generate worker wallet account\n', 'yellow'))

    if click.confirm(colored("\nWould you like to proceed?", 'white', attrs=['bold']), default=True):

        config_path = os.path.join(os.getcwd(), 'config.yaml')
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
        except yaml.YAMLError as e:
            print(colored(f"Error reading config file: {e}", 'red', attrs=['bold']))
            return

        worker_name = config['name']
        faucet_url = config['faucet_url']
        account_details = None
        if not config['worker']['mnemonic'] or not config['worker']['hex_coded_pk'] or not config['worker']['address']:
            account_details = create_worker_account(worker_name, faucet_url, 'worker')

        mnemonic = account_details[0] if account_details else config['worker']['mnemonic']
        hex_coded_pk = account_details[1] if account_details else config['worker']['hex_coded_pk']
        address = account_details[2] if account_details else config['worker']['address']
        worker_image_uri = config['worker']['image_uri']
        worker_image_tag = config['worker']['image_tag']
        boot_nodes = config['worker']['boot_nodes']
        chain_rpc_address = config['worker']['chain_rpc_address']
        chain_topic_id = config['worker']['chain_topic_id']

        if not config['worker']['mnemonic'] or not config['worker']['hex_coded_pk'] or not config['worker']['address']:
            config['worker']['mnemonic'] = mnemonic
            config['worker']['hex_coded_pk'] = hex_coded_pk
            config['worker']['address'] = address
            with open(config_path, 'w') as file:
                yaml.safe_dump(config, file)

        file_configs = [
            {
                "template_name": "worker.values.yaml.j2",
                "file_name": "worker.values.yaml",
                "context": {
                    "worker_image_uri": worker_image_uri, 
                    "worker_image_tag": worker_image_tag, 
                    "worker_name": worker_name, 
                    "boot_nodes": boot_nodes, 
                    "chain_rpc_address": chain_rpc_address, 
                    "chain_topic_id": chain_topic_id, 
                    "mnemonic": mnemonic, 
                    "hex_coded_pk": hex_coded_pk
                }
            }
        ]

        generate_all_files(env, file_configs, Command.DEPLOY)

        try:
            current_context = subprocess.run(["kubectl", "config", "current-context"], check=True, stdout=subprocess.PIPE, text=True).stdout.strip()
            print(colored("Current Kubernetes context: ", 'green') + colored(current_context, 'cyan'))
        except subprocess.CalledProcessError:
            print(colored("Failed to get current Kubernetes context. Is kubectl configured correctly?", 'red'))
            return

        try:
            subprocess.run(["helm", "version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(colored("Helm is already installed.", 'green'))
        except subprocess.CalledProcessError:
            try:
                print(colored("Attempting to install Helm...", 'yellow'))
                subprocess.run("curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash", shell=True, check=True)
                print(colored("Helm installed successfully.", 'green'))
            except subprocess.CalledProcessError as e:
                print(colored(f"Failed to install Helm: {e}", 'red'))
                return

        try:

            print(colored("Adding the 'upshot' Helm repository...", 'yellow'))
            subprocess.run(["helm", "repo", "add", "upshot", "https://upshot-tech.github.io/helm-charts"], check=True)
            subprocess.run(["helm", "repo", "update"], check=True)
            print(colored("'upshot' repository added and updated successfully.", 'green'))
            
            print(colored("Installing the Helm chart 'universal-helm' from 'upshot' repository...", 'yellow'))
            compose_dir = os.path.join(os.getcwd()) 
            values_file_path = os.path.join(compose_dir, "worker.values.yaml")
            if not os.path.exists(values_file_path):
                print(colored("Values file not found.", 'red'))
                return
            subprocess.run(["helm", "install", f"{worker_name}-worker", "upshot/universal-helm", "-f", values_file_path], check=True)
            print(colored("Helm chart 'universal-helm' installed successfully.", 'green'))
            
        except subprocess.CalledProcessError as e:
            print(colored(f"An error occurred: {e}", 'red'))
            return
    else:
        print(colored('Operation cancelled.', 'magenta'))

def deployValidator(env: Environment):
    """Deploy resource production kubernetes cluster"""

    print(colored('\nREQUIREMENTS', 'yellow', attrs=['bold']))
    print(colored('1. Ensure you have your Kubernetes cluster configured to your kubeconfig as the current context.', 'yellow'))
    print(colored('2. Ensure you have updated the ./config.yaml file\n'
                  '   Your wallet will be created for you and your mnemonic will be updated automagically\n', 'yellow'))

    print(colored('\nDEPENDENCIES', 'yellow', attrs=['bold']))
    print(colored('You must have the following tools installed in your machine to ensure successful deployment\n'
                  '1. helm: for deployment of worker into kubernetes cluster.\n'
                  '2. make: for installation of allora-chain to generate worker wallet account\n', 'yellow'))

    if click.confirm(colored("\nWould you like to proceed?", 'white', attrs=['bold']), default=True):

        config_path = os.path.join(os.getcwd(), 'config.yaml')
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
        except yaml.YAMLError as e:
            print(colored(f"Error reading config file: {e}", 'red', attrs=['bold']))
            return

        validator_name = config['name']
        faucet_url = config['faucet_url']
        account_details = None
        if not config['validator']['mnemonic'] or not config['validator']['hex_coded_pk'] or not config['validator']['address']:
            account_details = create_worker_account(validator_name, faucet_url, 'validator')

        mnemonic = account_details[0] if account_details else config['validator']['mnemonic']
        hex_coded_pk = account_details[1] if account_details else config['validator']['hex_coded_pk']
        address = account_details[2] if account_details else config['validator']['address']

        if not config['validator']['mnemonic'] or not config['validator']['hex_coded_pk'] or not config['validator']['address']:
            config['validator']['mnemonic'] = mnemonic
            config['validator']['hex_coded_pk'] = hex_coded_pk
            config['validator']['address'] = address
            with open(config_path, 'w') as file:
                yaml.safe_dump(config, file)

        file_configs = [
            {
                "template_name": "validator.values.yaml.j2",
                "file_name": "validator.values.yaml",
                "context": {
                    "name": validator_name, 
                    "hex_coded_pk": hex_coded_pk
                }
            }
        ]

        generate_all_files(env, file_configs, Command.DEPLOY)

        try:
            current_context = subprocess.run(["kubectl", "config", "current-context"], check=True, stdout=subprocess.PIPE, text=True).stdout.strip()
            print(colored("Current Kubernetes context: ", 'green') + colored(current_context, 'cyan'))
        except subprocess.CalledProcessError:
            print(colored("Failed to get current Kubernetes context. Is kubectl configured correctly?", 'red'))
            return

        try:
            subprocess.run(["helm", "version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(colored("Helm is already installed.", 'green'))
        except subprocess.CalledProcessError:
            try:
                print(colored("Attempting to install Helm...", 'yellow'))
                subprocess.run("curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash", shell=True, check=True)
                print(colored("Helm installed successfully.", 'green'))
            except subprocess.CalledProcessError as e:
                print(colored(f"Failed to install Helm: {e}", 'red'))
                return

        try:

            print(colored("Adding the 'upshot' Helm repository...", 'yellow'))
            subprocess.run(["helm", "repo", "add", "upshot", "https://upshot-tech.github.io/helm-charts"], check=True)
            subprocess.run(["helm", "repo", "update"], check=True)
            print(colored("'upshot' repository added and updated successfully.", 'green'))
            
            print(colored("Installing the Helm chart 'universal-helm' from 'upshot' repository...", 'yellow'))
            compose_dir = os.path.join(os.getcwd()) 
            values_file_path = os.path.join(compose_dir, "validator.values.yaml")
            if not os.path.exists(values_file_path):
                print(colored("Values file not found.", 'red'))
                return
            subprocess.run(["helm", "install", f"{validator_name}-validator", "upshot/universal-helm", "-f", values_file_path], check=True)
            print(colored("Helm chart 'universal-helm' installed successfully.", 'green'))
            
        except subprocess.CalledProcessError as e:
            print(colored(f"An error occurred: {e}", 'red'))
            return
    else:
        print(colored('Operation cancelled.', 'magenta'))

def check_docker_running():
    """Check if Docker daemon is running."""
    try:
        subprocess.run(['docker', 'info'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except subprocess.CalledProcessError:
        return False
