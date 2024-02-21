import os
import click
import subprocess
from jinja2 import Environment, FileSystemLoader
from importlib.resources import files
from enum import Enum, auto
import yaml
from termcolor import colored, cprint
from .utilities.utils import generate_all_files, create_worker_account, print_allora_banner, run_key_generate_command
from .utilities.typings import Command

template_path = files('allocmd').joinpath('templates')
env = Environment(loader=FileSystemLoader(template_path), autoescape=True)

@click.group()
def cli():
    """A CLI Tool that handles creation of an Allora Worker Node"""
    pass

@click.command()
@click.option('--name', required=True, help='Name of the worker.')
def init(name):
    """Initialize your Allora Worker Node with necessary boilerplates"""

    print_allora_banner()
    cprint("Welcome to the Allora CLI!", 'green', attrs=['bold'])
    print(colored("Allora CLI assists in the seamless creation and deployment of Allora worker nodes", 'yellow'))
    print(colored("to provide model inference to the Allora Chain.", 'yellow'))
    cprint(f"\nThis command will generate some files in the directory named '{name}'.", 'cyan')
    
    if click.confirm(colored("\nWould you like to proceed?", 'white', attrs=['bold']), default=True):
        cprint("\nProceeding with the creation of worker node directory...", 'green')

        head_peer_id = run_key_generate_command(name)

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
                "template_name": "docker-compose.yaml.j2",
                "file_name": "docker-compose.yaml",
                "context": {"head_peer_id": head_peer_id}
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
                "context": {"name": name}
            }
        ]

        generate_all_files(env, file_configs, Command.INIT, name)
    else:
        cprint("\nOperation cancelled.", 'red')

@click.command()
@click.option('--logs', is_flag=True, help="Follow logs immediately after starting services.")
def run(logs):
    """Starts worker and head nodes locally for development and testing"""

    compose_dir = os.getcwd()
    # compose_dir = os.path.join(os.getcwd(), 'checker')
    
    compose_file_path = os.path.join(compose_dir, 'docker-compose.yaml')
    if not os.path.exists(compose_file_path):
        print(colored("docker-compose.yaml file does not exist in the expected directory.", "red"))
        return
    
    try:
        print(colored("Starting worker and head node for local machine...", "yellow"))
        result = subprocess.run(['docker-compose', 'up', '--build', '-d'], cwd=compose_dir, check=True)
        
        if result.returncode == 0:
            print(colored("Nodes started successfully.", "green"))
            print("You can run " + colored("allocmd run --logs", "cyan") + " to follow the logs,")
            print("or " + colored("allocmd terminate", "cyan") + " to stop the local nodes.")
        else:
            print(colored("Starting node unsuccessful.", "red"))
    except subprocess.CalledProcessError as e:
        print(colored("Encountered error while starting nodes.", "red"))
        return

    if logs:
        click.echo(colored("Following logs (press Ctrl-C to stop logs)...", "blue"))
        try:
            subprocess.run(["docker-compose", "logs", "-f"], cwd=compose_dir, check=True)
        except subprocess.CalledProcessError:
            click.echo(colored("Error following logs.", "red"))

@click.command()
def terminate():
    """Terminates worker and head nodes locally"""

    compose_dir = os.getcwd()
    
    compose_file_path = os.path.join(compose_dir, 'docker-compose.yaml')
    if not os.path.exists(compose_file_path):
        print(colored("docker-compose.yaml file does not exist in the expected directory.", "red"))
        return
    
    try:
        print(colored("Terminating worker and head node on local machine...", "yellow"))
        result = subprocess.run(['docker-compose', 'stop'], cwd=compose_dir, check=True)
        
        if result.returncode == 0:
            print(colored("Nodes terminated successfully.", "green"))
        else:
            print(colored("Terminate node unsuccessful.", "red"))
    except subprocess.CalledProcessError as e:
        print(colored("Encountered error while terminating nodes.", "red"))
        return

@click.command()
def deploy():
    """Deploy worker node to your production kubernetes cluster"""

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

        worker_name = config['initialize']['name']
        accound_details = None
        if not config['deploy']['mnemonic'] or not config['deploy']['hex_coded_pk']:
            accound_details = create_worker_account(worker_name)

        mnemonic = accound_details[0] if accound_details else config['deploy']['mnemonic']
        hex_coded_pk = accound_details[1] if accound_details else config['deploy']['hex_coded_pk']
        worker_image_uri = config['deploy']['image_uri']
        worker_image_tag = config['deploy']['image_tag']
        boot_nodes = config['deploy']['boot_nodes']
        chain_rpc_address = config['deploy']['chain_rpc_address']
        chain_topic_id = config['deploy']['chain_topic_id']

        if not config['deploy']['mnemonic'] or not config['deploy']['hex_coded_pk']:
            config['deploy']['mnemonic'] = mnemonic
            config['deploy']['hex_coded_pk'] = hex_coded_pk
            with open(config_path, 'w') as file:
                yaml.safe_dump(config, file)

        file_configs = [
            {
                "template_name": "values.yaml.j2",
                "file_name": "values.yaml",
                "context": {"worker_image_uri": worker_image_uri, "worker_image_tag": worker_image_tag, "worker_name": worker_name, "boot_nodes": boot_nodes, "chain_rpc_address": chain_rpc_address, "chain_topic_id": chain_topic_id, "mnemonic": mnemonic, "hex_coded_pk": hex_coded_pk}
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
            values_file_path = os.path.join(compose_dir, "values.yaml")
            if not os.path.exists(values_file_path):
                print(colored("Values file not found.", 'red'))
                return
            subprocess.run(["helm", "install", worker_name, "upshot/universal-helm", "-f", values_file_path], check=True)
            print(colored("Helm chart 'universal-helm' installed successfully.", 'green'))
            
        except subprocess.CalledProcessError as e:
            print(colored(f"An error occurred: {e}", 'red'))
            return
    else:
        print(colored('Operation cancelled.', 'magenta'))

cli.add_command(init)
cli.add_command(run)
cli.add_command(terminate)
cli.add_command(deploy)

if __name__ == '__main__':
    cli()
