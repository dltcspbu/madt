
from .runtimes import docker_runtime, cluster_runtime

# TODO: remove map, calculate module name from runtime name
runtime_map = {
    'docker': docker_runtime,
    'cluster': cluster_runtime
}

def _get_runtime(name):
    return runtime_map[name]

def start_lab(*args, runtime='docker', **kwargs):
    """Starts a simulation of the lab.

    Currently, only docker runtime is supported.

    Args:
        lab_path: Directory containing the lab.
        prefix: Prefix to add to the container and subnets names configured in the lab
        image_prefix: An image prefix to use with image names configured in lab.
        timeout: time to pait until canceling the ping testing of the
            network and raising an excpetion.
        poll_interval: time to wait between ping tests of the network.

    Returns:
        A list of containers short_ids
    """

    return _get_runtime(runtime).start_lab(*args, **kwargs)

def stop_lab(*args, runtime='docker', **kwargs):
    """Stops the running simulation.

    Currently, only docker runtime is supported.
    lab_path, prefix, image_prefix='netsim', timeout=3*60, poll_interval=10

    Args:
        lab_path: Directory containing the lab.
        prefix: Prefix that was added to the container and subnets names
        configured in the lab.

    Returns:
        A list of containers short_ids
    """

    return _get_runtime(runtime).stop_lab(*args, **kwargs)

def restart_lab(*args, runtime='docker', **kwargs):
    """Stops the running simulation and starts it again.
        Arguments are same as those of start_lab"""

    runtime = _get_runtime(runtime)

    if hasattr(runtime, 'restart_lab'):
        return runtime.restart_lab(*args, **kwargs)
    else:
        runtime.stop_lab(*args, **kwargs)
        ret = start_lab(*args, **kwargs)

        print('\n...done', flush=True)

        return ret
