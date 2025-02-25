import boto3
import os

# Initialize the boto3 client
ec2 = boto3.resource('ec2', 
                    region_name='us-east-1',
                    aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
                    aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'], 
                    aws_session_token=os.environ['AWS_SESSION_TOKEN'])

# Create the EC2 instance
instance = ec2.create_instances(
    ImageId='ami-0f37c4a1ba152af46',  # Amazon Linux 2023, 64-bit ARM
    InstanceType='t2.micro',
    MinCount=1,
    MaxCount=1,
)[0]

# Wait for the instance to be running
print(f"Waiting for instance {instance.id} to start...")
instance.wait_until_running()

# Reload the instance to get the public IP
instance.reload()
public_ip = instance.public_ip_address

print(f"Instance is running at {public_ip}")

print(ec2.terminate_instances(InstanceIds=[instance.id]))