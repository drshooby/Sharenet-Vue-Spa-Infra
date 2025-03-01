import boto3
import os

try:
    AWS_REGION = "us-east-1"

    ssm_client = boto3.client("ssm", region_name=AWS_REGION)
    sts_client = boto3.client("sts", region_name=AWS_REGION)

    AWS_ACCOUNT_ID = sts_client.get_caller_identity()["Account"]

    ECR_REPO_BACKEND = f"{AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com/sharenet_vue_spa_backend:latest"
    ECR_REPO_FRONTEND = f"{AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com/sharenet_vue_spa_frontend:latest"

    commands = [
        f"aws ecr get-login-password --region {AWS_REGION} | docker login --username AWS --password-stdin {AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com",

        # Pull the latest
        f"docker pull {ECR_REPO_BACKEND}",
        f"docker pull {ECR_REPO_FRONTEND}",

        # Kill old
        "docker stop frontend backend || true",
        "docker rm -f frontend backend || true",

        # Bring up new
        f"docker run -d --name backend -p 5000:5000 {ECR_REPO_BACKEND}",
        f"docker run -d --name frontend -p 8080:8080 {ECR_REPO_FRONTEND}",

        "docker ps -a"
    ]

    response = ssm_client.send_command(
        InstanceIds=[os.environ['INSTANCE_ID']],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": commands},
    )

    print(response)
    print(f"Deployment initiated! 💎")

except Exception as e:
    print(f"{e} 🚩")
    exit(1)

finally:
    print(f"done")