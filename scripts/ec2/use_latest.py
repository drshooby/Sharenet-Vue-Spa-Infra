import io
import os

import boto3
import paramiko

try:
    # Initialize the boto3 client
    ec2_client = boto3.client('ec2',
                        region_name='us-east-1',
                        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
                        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
                        aws_session_token=os.environ['AWS_SESSION_TOKEN'])

    instance_id = None

    describe_response = ec2_client.describe_instances(InstanceIds=[instance_id])

    public_ip = describe_response['Reservations'][0]['Instances'][0].get('PublicIpAddress', None)
    if not public_ip:
        error_occurred = True
        raise Exception("No public IP address for instance", instance_id)

    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    private_key_str = os.environ["PEM"].replace("\\n", "\n")
    pkey = paramiko.RSAKey.from_private_key(io.StringIO(private_key_str))
    ssh_client.connect(public_ip, username="ec2-user", pkey=pkey, look_for_keys=False)

    print("SSH Connected.")

    ecr_login_cmd = "aws ecr get-login-password --region us-east-1"

    _, ecr_stdout, ecr_stderr = ssh_client.exec_command(ecr_login_cmd)
    err = ecr_stderr.read().decode()
    if err:
        raise Exception(f"ECR login failed: {err}")

    ecr_credentials = ecr_stdout.read().decode().strip()

    docker_login_cmd = f"echo {ecr_credentials} | docker login --username AWS --password-stdin {describe_response['Reservations'][0]['Instances'][0]['ImageId']}.dkr.ecr.us-east-1.amazonaws.com"

    _, _, docker_stderr = ssh_client.exec_command(docker_login_cmd)
    err = docker_stderr.read().decode()
    if err:
        raise Exception(f"Docker login failed: {err}")

    frontend_repo = "sharenet_vue_spa/frontend"
    backend_repo = "sharenet_vue_spa/backend"

    frontend_image_uri = f"{describe_response['Reservations'][0]['Instances'][0]['ImageId']}.dkr.ecr.us-east-1.amazonaws.com/{frontend_repo}:latest"
    backend_image_uri = f"{describe_response['Reservations'][0]['Instances'][0]['ImageId']}.dkr.ecr.us-east-1.amazonaws.com/{backend_repo}:latest"

    pull_frontend_cmd = f"docker pull {frontend_image_uri}"
    pull_backend_cmd = f"docker pull {backend_image_uri}"

    _, _, pull_stderr = ssh_client.exec_command(pull_frontend_cmd)
    err = pull_stderr.read().decode()
    if err:
        raise Exception(f"Pull frontend failed: {err}")

    _, _, pull_stderr = ssh_client.exec_command(pull_backend_cmd)
    err = pull_stderr.read().decode()
    if err:
        raise Exception(f"Pull backend failed: {err}")

    print("LATEST IMAGE PULLED SUCCESSFULLY ✨")

except Exception as e:
    print(f"{e} 🚩")
    exit(1)