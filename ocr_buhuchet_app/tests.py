import subprocess

IAM_TOKEN = subprocess.check_output(["yc", "iam", "create-token"], shell=True).decode("utf-8").strip('\n')
print(IAM_TOKEN)
