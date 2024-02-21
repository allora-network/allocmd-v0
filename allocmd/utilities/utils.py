import os
import click
import subprocess
from jinja2 import Environment
from importlib.resources import files
from termcolor import colored, cprint
import time
import shutil 
from .typings import Command

def create_worker_account(worker_name):
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
    
    make_path = shutil.which('make')
    if make_path:
        gopath_output = subprocess.run(['go', 'env', 'GOPATH'], capture_output=True, text=True, check=True)
        gopath = gopath_output.stdout.strip()
        new_path = os.environ['PATH'] + os.pathsep + os.path.join(gopath, 'bin')
        env = os.environ.copy()
        env['PATH'] = new_path
        subprocess.run(['make', 'install'], 
                        cwd=allora_chain_dir, 
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)
        subprocess.run(['make', 'init'], 
                        cwd=allora_chain_dir,
                        env=env, 
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)

        key_path = os.path.join(os.getcwd(), f'{worker_name}.key')
        with open(key_path, 'w') as file:
            subprocess.run(['allorad', 'keys', 'add', worker_name, '--keyring-backend', 'test'], 
                            cwd=allora_chain_dir,
                            env=env, 
                            stdout=file, 
                            stderr=subprocess.STDOUT, 
                            check=True)

        with open(key_path, 'r') as file:
            lines = file.readlines()

        mnemonic = lines[-1].strip()
        
        print(colored(f"keys created for this worker. please check {worker_name}.keys for your address and mnemonic", "green"))
        return mnemonic
    else:
        print(colored("'make' is not available in the system's PATH. Please install it or check your PATH settings.", "red"))
        return ''

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

def generate_all_files(env: Environment, file_configs, command: Command, worker_name = ''):
    if command == Command.INIT:
        cprint(f"Bootstraping '{worker_name}' directory...", 'cyan')
        time.sleep(1) 

    for config in file_configs:
        template = env.get_template(config["template_name"])

        if command == Command.INIT:
            file_path = os.path.join(os.getcwd(), f'{worker_name}/{config["file_name"]}')
        elif command == Command.DEPLOY: 
            file_path = os.path.join(os.getcwd(), f'{config["file_name"]}')

        content = template.render(**config["context"])
        with open(file_path, 'w') as f:
            f.write(content)

    if command == Command.INIT:
        cprint("\nAll files bootstrapped successfully. ALLORA!!!", 'green', attrs=['bold'])

def run_key_generate_command(worker_name):
    command = (
        f'docker run -it --entrypoint=bash -v "$(pwd)/{worker_name}/data":/data '
        '696230526504.dkr.ecr.us-east-1.amazonaws.com/allora-inference-base:dev-latest '
        '-c "mkdir -p /data/head/key /data/worker/key && (cd /data/head/key && allora-keys) && (cd /data/worker/key && allora-keys)"'
    )
    try:
        subprocess.run(command, shell=True, check=True)
        peer_id_path = os.path.join(os.getcwd(), f'{worker_name}/data/head/key', 'identity')
        with open(peer_id_path, 'r') as file:
            cprint(f"local workers identity generated successfully.", 'cyan')
            head_peer_id = file.read().strip()
            return head_peer_id
    except subprocess.CalledProcessError as e:
        click.echo(f"error generating local workers identity: {e}", err=True)
