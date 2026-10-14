import ipaddress


class DockerRuntimeError(RuntimeError):
    pass


def get_docker_sdk():
    try:
        import docker
    except ImportError as exc:
        raise DockerRuntimeError(
            "Docker SDK is required for container operations. "
            "Install it with `python -m pip install docker`."
        ) from exc

    if not hasattr(docker, "from_env") or not hasattr(docker, "types"):
        raise DockerRuntimeError(
            "Docker SDK is not importable as the `docker` package. "
            "Install PyPI package `docker` in the active Python environment."
        )
    return docker


def create_docker_client():
    return get_docker_sdk().from_env()


class DockerNetworkBackend:
    def __init__(self, group_label, client=None):
        self.group_label = group_label
        self._client = client
        self._docker = None

    @property
    def docker(self):
        if self._docker is None:
            self._docker = get_docker_sdk()
        return self._docker

    @property
    def client(self):
        if self._client is None:
            self._client = create_docker_client()
        return self._client

    def list_group_containers(self):
        return self.client.containers.list(all=True, filters={"label": f"group={self.group_label}"})

    def list_group_networks(self):
        return self.client.networks.list(filters={"label": f"group={self.group_label}"})

    def stop_and_remove_container(self, container):
        try:
            container.stop()
            container.remove()
            print(f"-> 容器{container.name}已停止并删除")
        except self.docker.errors.APIError as exc:
            print(f"Failed to stop or remove container {container.name}: {str(exc)}")

    def create_bridge_network(self, net_name, subnet):
        subnet = ipaddress.ip_network(subnet)
        return self.client.networks.create(
            net_name,
            driver="bridge",
            labels={"group": self.group_label},
            ipam=self.docker.types.IPAMConfig(
                pool_configs=[
                    self.docker.types.IPAMPool(
                        subnet=str(subnet),
                    )
                ]
            ),
        )

    def create_macvlan_network(self, net_name, parent, subnet, gateway):
        return self.client.networks.create(
            net_name,
            driver="macvlan",
            options={"parent": str(parent)},
            labels={"group": self.group_label},
            ipam=self.docker.types.IPAMConfig(
                driver="default",
                pool_configs=[
                    self.docker.types.IPAMPool(
                        subnet=str(subnet),
                        gateway=str(gateway),
                    )
                ],
            ),
        )
