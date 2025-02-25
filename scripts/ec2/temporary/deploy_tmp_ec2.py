import boto3
import os

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

# Kill the instance
terminate_response = ec2_client.terminate_instances(InstanceIds=[instance_id])
print(terminate_response)