import boto3
import os

try:
    AWS_REGION = "us-east-1"

    ssm_client = boto3.client("ssm", region_name=AWS_REGION)
    sts_client = boto3.client("sts", region_name=AWS_REGION)

    AWS_ACCOUNT_ID = sts_client.get_caller_identity()["Account"]

    ECR_REPO_BACKEND = f"{AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com/sharenet_vue_spa_backend:latest"
    ECR_REPO_FRONTEND = f"{AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com/sharenet_vue_spa_frontend:latest"

    # Backend vars
    MYSQL_HOST = os.environ["MYSQL_HOST"]
    MYSQL_USER = os.environ["MYSQL_USER"]
    MYSQL_PASSWORD = os.environ["MYSQL_PASSWORD"]
    MYSQL_DATABASE = os.environ["MYSQL_DATABASE"]
    MYSQL_TABLE = os.environ["MYSQL_TABLE"]
    BACK_PORT = os.environ["BACK_PORT"]

    # Frontend var
    VUE_APP_GOOGLE_MAPS_API_KEY = os.environ["VUE_APP_GOOGLE_MAPS_API_KEY"]

    commands = [
        f"aws ecr get-login-password --region {AWS_REGION} | docker login --username AWS --password-stdin {AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com",

        # Pull the latest
        f"docker pull {ECR_REPO_BACKEND}",
        f"docker pull {ECR_REPO_FRONTEND}",

        # Kill old
        "docker stop frontend backend || true",
        "docker rm -f frontend backend || true",

        # Bring up new backend
        f"docker run -d --name backend -p 5000:5000 "
        f"-e MYSQL_HOST={MYSQL_HOST} -e MYSQL_USER={MYSQL_USER} -e MYSQL_PASSWORD={MYSQL_PASSWORD} "
        f"-e MYSQL_DATABASE={MYSQL_DATABASE} -e MYSQL_TABLE={MYSQL_TABLE} -e BACK_PORT={BACK_PORT} "
        f"{ECR_REPO_BACKEND}",

        # Bring up new frontend
        f"docker run -d --name frontend -p 8080:8080 "
        f"-e VUE_APP_GOOGLE_MAPS_API_KEY={VUE_APP_GOOGLE_MAPS_API_KEY} "
        f"{ECR_REPO_FRONTEND}",

        "docker ps -a"
    ]

    response = ssm_client.send_command(
        InstanceIds=[os.environ['INSTANCE_ID']],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": commands},
    )

    print(response)
    print(f"Deployment initiated! 💎")

except KeyError as e:
    print(f"Missing environment variable: {e} 🔒")
    exit(1)
except Exception as e:
    print(f"{e} 🚩")
    exit(1)

finally:
    print("done")