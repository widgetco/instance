from datetime import datetime
import redis
import requests
import os
import subprocess

def get_metadata_from_host(key):
    return requests.get("http://169.254.169.250/latest/meta-data/" + key).text

appredis = redis.StrictRedis.from_url(get_metadata_from_host("redis-url"))
job_queue = get_metadata_from_host("job-queue")
instance_id = get_metadata_from_host("instance-id")

def rlog(message):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = instance_id + ":" + stamp + ":" + str(message)
    print(line)
    appredis.rpush(job_queue + ":logs", line)


def clone_repo_if_not_exists(repo_clone_path, github_token, repo_name, instance_id):
    # checks to see if directory 'repo_name' exists
    # if it does not, clone the repo
    # repo_clone_path is like "owner/repo.git"
    # github_token is the github token for the repo
    cmd = ("git clone https://%s@github.com/" % github_token) + repo_clone_path + " " + repo_name
    if not os.path.exists(repo_name):
        rlog("Cloning repo {}".format(cmd), instance_id)
        os.system(cmd)

def pull_and_reinstall_crontab(repo_name, instance_id):
    os.system("cd {} && git pull".format(repo_name))
    rlog("Pulled repo {}".format(repo_name))
    if os.path.exists("%s/Cronfile" % repo_name):
        rlog("Cronfile exists, reinstalling crontab")
        os.system("crontab Cronfile")
        rlog("Reinstalled crontab", instance_id)

def main():
    github_token = get_metadata_from_host("github-token")
    repo_clone_url = get_metadata_from_host("repo-clone-url")
    repo_name = get_metadata_from_host("repo-name")
    
    rlog("Started... {}".format(locals()))

    clone_repo_if_not_exists(repo_clone_url, github_token, repo_name, instance_id)
    pull_and_reinstall_crontab(repo_name, instance_id)
    rlog("Pulled repo {}".format(repo_name))

    rlog("Init complete")

    while True:
        rlog("Waiting for job...")
        job = appredis.blpop(job_queue, timeout=0)[1].decode("utf-8")
        rlog("Got job: {}".format(job))
        # do the job
        out = subprocess.check_output("cd {} && {}".format(repo_name, job), shell=True)
        rlog(out)
        rlog("Job complete.")



if __name__ == "__main__":
    main()
