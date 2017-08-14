import time

import requests

from test_packaging import (
    _skipif_insufficient_resources
)

# TODO
DEMO_RESOURCE_REQUIREMENTS = {
    'number_of_nodes': 5,
    'node': {
        'disk': 0,
        'mem': 0,
        'cpus': 1
    }
}

CASSANDRA_STABLE_VERSION = '1.0.12-2.2.5'
KAFKA_STABLE_VERSION = '1.1.9-0.10.0.0'
# This works with DC/OS 1.10
MARATHON_LB_STABLE_VERSION = '1.10.0'
ZEPPELIN_STABLE_VERSION = '0.6.0'

PUBLIC_IP_DEFINITION = {
    "id": "/public-ip",
    "cmd": "curl http://169.254.169.254/latest/meta-data/public-ipv4 && sleep 3600",
    "cpus": 0.25,
    "mem": 32,
    "instances": 1,
    "acceptedResourceRoles": [
        "slave_public"
    ]
}


# TODO Which parameters to use for retrying.retry?
def _get_tweeter_app_definition():
    response = requests.get('https://raw.githubusercontent.com/mesosphere/tweeter/master/tweeter.json')
    return response.json()


def _get_post_tweets_app_definition():
    response = requests.get('https://raw.githubusercontent.com/mesosphere/tweeter/master/post-tweets.json')
    return response.json()


def _get_tweet_count(address):
    response = requests.get(address)
    return response.text.count('tweet-content')


def test_tweeter_demo_oss(dcos_api_session):
    """Step through setup and run the Tweeter demo application. See https://github.com/mesosphere/tweeter
    Should be equivalent to the cli script. It passes if service and app installations are successful and the
    post_tweets application successfully posts tweets to the tweeter webapp.

    Note that the Zeppelin notebook is not run, nor is it set up with cores_max parameter to 8 as noted in the docs for
    manually running this.
    """
    _skipif_insufficient_resources(dcos_api_session, DEMO_RESOURCE_REQUIREMENTS)
    print("Installing cassandra")
    dcos_api_session.cosmos.install_package('cassandra', CASSANDRA_STABLE_VERSION)
    print("Installing kafka")
    dcos_api_session.cosmos.install_package('kafka', KAFKA_STABLE_VERSION)
    print("Installing marathon-lb")
    dcos_api_session.cosmos.install_package('marathon-lb', MARATHON_LB_STABLE_VERSION)
    print("Installing zeppelin")
    dcos_api_session.cosmos.install_package('zeppelin', ZEPPELIN_STABLE_VERSION)
    print("Waiting for requirements to deploy")
    dcos_api_session.marathon.wait_for_deployments_complete()

    tweeter_app_definition = _get_tweeter_app_definition()
    print("Deploying tweeter")
    print(str(tweeter_app_definition))
    dcos_api_session.marathon.deploy_app(tweeter_app_definition)

    post_tweets_definition = _get_post_tweets_app_definition()
    print("Deploying post_tweets")
    print(post_tweets_definition)
    # post-tweets does not define a health check
    dcos_api_session.marathon.deploy_app(post_tweets_definition, check_health=False)
    # wait for some of the 100k+ tweets to be posted
    time.sleep(30)

    # The tutorial has you use the public endpoint, but this test is run from the cluster itself, so the app can simply
    # be accessed from the private endpoint as configured in the app definition.
    ip = 'http://1.1.1.1:30000'
    tweet_count = _get_tweet_count(ip)
    assert tweet_count > 0, "No tweets found!"
    print("Success: Found {} posted tweets".format(tweet_count))
