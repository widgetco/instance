import redis
import requests
import os

SLACK_URL = 'https://hooks.slack.com/services/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'

def slack(message, instance_id):
    print(message)
    data = {'text': ('guest *%s*\n' % instance_id) + str(message)}
    requests.post(SLACK_URL, json=data)

def get_metadata_from_host(key):
    return requests.get("169.254.169.250/latest/meta-data/" + key).text

def clone_repo_if_not_exists(repo_clone_path, github_token, repo_name, instance_id):
    # checks to see if directory 'repo_name' exists
    # if it does not, clone the repo
    # repo_clone_path is like "owner/repo.git"
    # github_token is the github token for the repo
    cmd = ("git clone https://%s@github.com/" % github_token) + repo_clone_path + " " + repo_name
    if not os.path.exists(repo_name):
        slack("Cloning repo {}".format(cmd), instance_id)
        os.system(cmd)


def main():
    instance_id = get_metadata_from_host("instance-id")
    github_token = get_metadata_from_host("github-token")
    repo_clone_url = get_metadata_from_host("repo-clone-url")
    repo_name = get_metadata_from_host("repo-name")
    job_queue = get_metadata_from_host("job-queue")
    redis_url = get_metadata_from_host("redis-url")
    print("Started... {}".format(locals()))
    slack("Started... {}".format(locals()), instance_id)

    clone_repo_if_not_exists(repo_clone_url, github_token, repo_name, instance_id)
    os.system("cd {} && git pull".format(repo_name))
    print(os.listdir("."))
    slack("Pulled repo {}".format(repo_name), instance_id)

    appredis = redis.StrictRedis.from_url(redis_url)
    appredis.rpush(job_queue + ":logs", "Restarted " + instance_id)

    while True:
        print("Waiting for job...")
        job = appredis.blpop(job_queue, timeout=0)[1].decode("utf-8")
        print("Got job: {}".format(job))
        appredis.rpush(job_queue + ":logs", "Got job: " + job)
        # do the job
        appredis.rpush(job_queue + ":logs", "Finished job: " + job)



if __name__ == "__main__":
    main()
