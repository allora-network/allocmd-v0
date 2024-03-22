import os
import click
import subprocess
from jinja2 import Environment, FileSystemLoader
from importlib.resources import files
from termcolor import colored, cprint
from .utilities.utils import generate_all_files, print_allora_banner, run_key_generate_command, deployWorker, deployValidator, generateWorkerAccount, generateProdCompose
from .utilities.typings import Command
from .utilities.constants import cliVersion

template_path = files('allocmd').joinpath('templates')
env = Environment(loader=FileSystemLoader(template_path), autoescape=True)

@click.group()
@click.version_option(version=cliVersion, prog_name='allocmd', message='%(prog)s version %(version)s')
def cli():
    """A CLI Tool that handles creation of an Allora Worker Node"""
    pass

@click.command()
@click.option('--env', 'environment', required=True, type=click.Choice(['dev', 'prod']), help='Environment to generate for')
@click.option('--name', required=False, help='Name of the worker.')
@click.option('--topic', required=False, type=int, help='The topic ID the worker is registered with.')
def init(environment, name=None, topic=None):
    """Initialize your Allora Worker Node with necessary boilerplates"""

    if environment == 'dev':
        if topic is None:
            cprint("You must provide topic id when running development init.", 'red')
            return
        elif name is None:
            cprint("You must provide name when running development init.", 'red')
            return


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
                    "template_name": "dev-docker-compose.yaml.j2",
                    "file_name": "dev-docker-compose.yaml",
                    "context": {"head_peer_id": head_peer_id, "topic_id": topic}
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
                    "context": {"name": name, "topic_id": topic}
                }
            ]

            generate_all_files(env, file_configs, Command.INIT, name)

            generateWorkerAccount(name)
        else:
            cprint("\nOperation cancelled.", 'red')
    elif environment == 'prod':
        devComposePath = os.path.join(os.getcwd(), 'dev-docker-compose.yaml')
        if not os.path.exists(devComposePath):
            cprint("You must initialize the worker on dev please run allocmd init --env dev --name <worker name> --topic <topic id> and then run the prod init in the directory created", 'red')
        else:
            generateProdCompose(env)

# @click.command()
# @click.option('--logs', is_flag=True, help="Follow logs immediately after starting services.")
def run(logs):
    """Starts worker and head nodes locally for development and testing"""

    compose_dir = os.getcwd()
    # compose_dir = os.path.join(os.getcwd(), 'checker')
    
    compose_file_path = os.path.join(compose_dir, 'dev-docker-compose.yaml')
    if not os.path.exists(compose_file_path):
        print(colored("dev-docker-compose.yaml file does not exist in the expected directory.", "red"))
        return
    
    try:
        print(colored("Starting worker and head node for local machine...", "yellow"))
        result = subprocess.run(['docker-compose', '-f', 'dev-docker-compose.yaml', 'up', '--build', '-d'], cwd=compose_dir, check=True)
        
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
            subprocess.run(["docker-compose", '-f', 'dev-docker-compose.yaml', "logs", "-f"], cwd=compose_dir, check=True)
        except subprocess.CalledProcessError:
            click.echo(colored("Error following logs.", "red"))

# @click.command()
def terminate():
    """Terminates worker and head nodes locally"""

    compose_dir = os.getcwd()
    
    compose_file_path = os.path.join(compose_dir, 'dev-docker-compose.yaml')
    if not os.path.exists(compose_file_path):
        print(colored("dev-docker-compose.yaml file does not exist in the expected directory.", "red"))
        return
    
    try:
        print(colored("Terminating worker and head node on local machine...", "yellow"))
        result = subprocess.run(['docker-compose', '-f', 'dev-docker-compose.yaml', 'stop'], cwd=compose_dir, check=True)
        
        if result.returncode == 0:
            print(colored("Nodes terminated successfully.", "green"))
        else:
            print(colored("Terminate node unsuccessful.", "red"))
    except subprocess.CalledProcessError as e:
        print(colored("Encountered error while terminating nodes.", "red"))
        return

# @click.command()
# @click.option('--type', 'type_', required=True, type=click.Choice(['validator', 'worker'], case_sensitive=False), help='The allora resource type you want to deploy.')
def deploy(type_):
    """Deploy resource production kubernetes cluster"""

    if type_ == 'worker':
        deployWorker(env)
    elif type_ == 'validator':
        deployValidator(env)
    else:
        click.echo("Invalid resource type specified.")


    
cli.add_command(init)
# cli.add_command(run)
# cli.add_command(terminate)
# cli.add_command(deploy)

if __name__ == '__main__':
    cli()
