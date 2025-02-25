import boto3
import os
import time
import paramiko
import tarfile
import io

instance_id = None
error_occured = False
try:
    # Initialize the boto3 client
    ec2_client = boto3.client('ec2', 
                        region_name='us-east-1',
                        aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
                        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'], 
                        aws_session_token=os.environ['AWS_SESSION_TOKEN'])
    
    # Create the EC2 instance
    response = ec2_client.run_instances(
        ImageId='ami-04681163a08179f28',  # Amazon Linux 2 AMI (64-bit x86)
        InstanceType='t2.micro',
        MinCount=1,
        MaxCount=1,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': 'Smoke Test'
                    },
                ]
            },
        ]
    )

    instance_id = response['Instances'][0]['InstanceId']

    print(f"Waiting for instance {instance_id} to start...")
    waiter = ec2_client.get_waiter('instance_running')
    waiter.wait(InstanceIds=[instance_id])

    describe_response = ec2_client.describe_instances(InstanceIds=[instance_id])
    public_ip = describe_response['Reservations'][0]['Instances'][0].get('PublicIpAddress', 'No public IP')

    print(f"Instance is running at {public_ip}")

    def create_tarball(source):
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
            tar.add(source, arcname=os.path.basename(source))
        tar_buffer.seek(0)
        return tar_buffer

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    max_attempts = 5
    connected = False

    private_key = paramiko.RSAKey.from_private_key(io.StringIO(os.environ['PEM']))

    for attempt in range(max_attempts):
        try:
            ssh.connect(public_ip, username='ec2-user', pkey=private_key)
            connected = True
            break
        except Exception as e:
            print(e)
            time.sleep(5)

    if not connected:
        raise Exception("Could not connect to the instance")
    
    app_tarball = create_tarball('app')

    sftp = ssh.open_sftp()
    sftp.putfo(app_tarball, 'app.tar.gz')
    sftp.close()

    stdin, stdout, stderr = ssh.exec_command('tar -xzf app.tar.gz')
    print(stdout.read().decode())
    print(stderr.read().decode())

    ssh.close()

    print("File transfer complete 🎉")

except Exception as e:
    print(e + "🚩")
    error_occured = True
finally:
    # Kill the instance
    if instance_id:
        terminate_response = ec2_client.terminate_instances(InstanceIds=[instance_id])
        print(terminate_response)

if error_occured:
    exit(1)