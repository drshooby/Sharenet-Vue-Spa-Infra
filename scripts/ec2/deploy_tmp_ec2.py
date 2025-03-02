import base64
import io
import os
import tarfile

import boto3
import paramiko

instance_id = None
error_occurred = False
ec2_client = None

print("Deploying app to a temporary EC2 instance for smoke tests...")

try:
    # Initialize the boto3 client
    ec2_client = boto3.client('ec2',
                        region_name='us-east-1',
                        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
                        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
                        aws_session_token=os.environ['AWS_SESSION_TOKEN'])

    # This sets the environment vars in the EC2 machine for the tests
    user_data_script = f"""
    #!/bin/bash
    echo 'export MYSQL_DATABASE="{os.environ['MYSQL_DATABASE']}"' >> /etc/profile.d/app_env.sh
    echo 'export MYSQL_PASSWORD="{os.environ['MYSQL_PASSWORD']}"' >> /etc/profile.d/app_env.sh
    echo 'export MYSQL_ROOT_PASSWORD="{os.environ['MYSQL_ROOT_PASSWORD']}"' >> /etc/profile.d/app_env.sh
    echo 'export MYSQL_TABLE="{os.environ['MYSQL_TABLE']}"' >> /etc/profile.d/app_env.sh
    echo 'export MYSQL_USER="{os.environ['MYSQL_USER']}"' >> /etc/profile.d/app_env.sh
    echo 'export MYSQL_HOST="{os.environ['MYSQL_HOST']}"' >> /etc/profile.d/app_env.sh
    echo 'export VUE_APP_GOOGLE_MAPS_API_KEY="{os.environ['VUE_APP_GOOGLE_MAPS_API_KEY']}"' >> /etc/profile.d/app_env.sh
    echo 'export API_URL="{os.environ['API_URL']}"' >> /etc/profile.d/app_env.sh
    echo 'export ALLOWED_ORIGINS="{os.environ['ALLOWED_ORIGINS']}"' >> /etc/profile.d/app_env.sh
    source /etc/profile.d/app_env.sh
    chmod +x /etc/profile.d/app_env.sh
    """

    # Encode the user data script in base64
    # This is an option in AWS when entering the script manually online so add it here
    encoded_user_data = base64.b64encode(user_data_script.encode()).decode()

    # Create the EC2 instance
    response = ec2_client.run_instances(
        ImageId='ami-06aa41e39302ba3db',  # Amazon Linux 2 AMI (64-bit x86) with Docker and Compose
        InstanceType='t2.micro',
        MinCount=1,
        MaxCount=1,
        KeyName='vockey',
        UserData=encoded_user_data,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': 'Temporary EC2 Instance (Smoke Test)'
                    },
                ]
            },
        ]
    )

    instance_id = response['Instances'][0]['InstanceId']

    print(f"Waiting for instance {instance_id} to start...")

    waiter = ec2_client.get_waiter('instance_status_ok')
    waiter.wait(InstanceIds=[instance_id])

    print(f"Instance {instance_id} is ready")

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

    def create_tarball(source):
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
            tar.add(source, arcname=os.path.basename(source))
        tar_buffer.seek(0)
        return tar_buffer

    # Tarball since it makes more sense to package up the code and do a little compression prior to sending for speed
    app_tarball = create_tarball('app')

    sftp = ssh_client.open_sftp()
    sftp.putfo(app_tarball, 'app.tar.gz')
    sftp.close()

    _, _, stderr = ssh_client.exec_command('tar -xzf app.tar.gz')
    err = stderr.read().decode()
    if err:
        raise Exception(f"Failed to extract tarball: {err}")

    print("File transfer complete 🎉")

    stdin, stdout, stderr = ssh_client.exec_command('ls -a')
    print("Files on server:")
    print(stdout.read().decode())

    # Change directory and run docker-compose
    _, docker_out, docker_err = ssh_client.exec_command('cd app && docker compose up -d && docker exec app-backend-1 npm test')
    docker_stdout = docker_out.read().decode()
    docker_stderr = docker_err.read().decode()

    # Paramiko has this weird thing where docker warnings count as errors, so check both to be sure
    if "PASS" in docker_stderr or "PASS" in docker_stdout:
        print("SMOKE TESTS PASS ✨")
    else:
        raise Exception("Tests had problems!", docker_stderr)
    
    # Kill containers
    _, stdout, stderr = ssh_client.exec_command('cd app && docker compose down')
    docker_down_stderr = stderr.read().decode()
    if docker_down_stderr:
        print(f"Docker-compose down error: {docker_down_stderr}")
    else:
        print("Docker-compose down ran successfully")

    ssh_client.close()

except Exception as e:
    print(f"{e} 🚩")
    error_occurred = True
finally:
    #Kill the instance
    if instance_id:
        terminate_response = ec2_client.terminate_instances(InstanceIds=[instance_id])
        print(terminate_response)
    print("done")

if error_occurred:
    exit(1)
