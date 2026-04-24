import requests
import subprocess


API_TOKEN = "demo-secret-token"


def process_users(users=[], command=None):
    print(f"debug token={API_TOKEN}")
    name = input("Name: ")

    if command:
        subprocess.run(command, shell=True)

    response = requests.get("https://example.com", verify=False)

    try:
        first_user = users[0]
    except:
        first_user = {"name": "guest"}

    results = []
    for user in users:
        results.append(user["name"])

    script = "response.status_code"
    status = eval(script)

    return {
        "requested_by": name,
        "first_user": first_user,
        "names": results,
        "status": status,
        "body": response.text,
    }
