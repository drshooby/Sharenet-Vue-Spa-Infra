import boto3
import os

print("Deploying app with latest images...")

try:
    AWS_REGION = "us-east-1"

    ssm_client = boto3.client(
        "ssm",
        region_name=AWS_REGION,
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        aws_session_token=os.environ["AWS_SESSION_TOKEN"]
    )

    sts_client = boto3.client(
        "sts",
        region_name=AWS_REGION,
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        aws_session_token=os.environ["AWS_SESSION_TOKEN"]
    )

    AWS_ACCOUNT_ID = sts_client.get_caller_identity()["Account"]

    ECR_REPO_BACKEND = f"{AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com/sharenet_vue_spa/backend:latest"
    ECR_REPO_FRONTEND = f"{AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com/sharenet_vue_spa/frontend:latest"

    # Backend vars
    MYSQL_HOST = os.environ["MYSQL_HOST"]
    MYSQL_USER = os.environ["MYSQL_USER"]
    MYSQL_PASSWORD = os.environ["MYSQL_PASSWORD"]
    MYSQL_DATABASE = os.environ["MYSQL_DATABASE"]
    MYSQL_TABLE = os.environ["MYSQL_TABLE"]

    # Frontend var
    VUE_APP_GOOGLE_MAPS_API_KEY = os.environ["VUE_APP_GOOGLE_MAPS_API_KEY"]

    INSTANCE_ID = os.environ["INSTANCE_ID"]

    commands = [
        f"aws ecr get-login-password --region {AWS_REGION} | docker login --username AWS --password-stdin {AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com",

        # Pull the latest images
        f"docker pull {ECR_REPO_BACKEND}",
        f"docker pull {ECR_REPO_FRONTEND}",

        # Kill old containers (if they exist)
        "docker stop frontend backend || true",
        "docker rm -f frontend backend || true",

        # Bring up new backend container
        f"docker run -d --name backend -p 5000:5000 "
        f"-e MYSQL_HOST={MYSQL_HOST} -e MYSQL_USER={MYSQL_USER} -e MYSQL_PASSWORD={MYSQL_PASSWORD} "
        f"-e MYSQL_DATABASE={MYSQL_DATABASE} -e MYSQL_TABLE={MYSQL_TABLE} "
        f"{ECR_REPO_BACKEND}",

        # Bring up new frontend container
        f"docker run -d --name frontend -p 8080:8080 "
        f"-e VUE_APP_GOOGLE_MAPS_API_KEY={VUE_APP_GOOGLE_MAPS_API_KEY} "
        f"{ECR_REPO_FRONTEND}",

        # Cleanup
        "docker image prune -a -f",
    ]

    waiter = ssm_client.get_waiter('command_executed')

    response = ssm_client.send_command(
        InstanceIds=[INSTANCE_ID],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": commands},
    )

    command_id = response['Command']['CommandId']

    # Wait for commands to do their thing or this all breaks
    waiter.wait(
        CommandId=command_id,
        InstanceId=INSTANCE_ID
    )

    output = ssm_client.get_command_invocation(
        CommandId=command_id,
        InstanceId=INSTANCE_ID,
    )

    print(f"Deployment initiated! 💎")

except KeyError as e:
    print(f"Missing environment variable: {e} 🔒")
    exit(1)
except Exception as e:
    print(f"{e} 🚩")
    exit(1)

finally:
    print("done")