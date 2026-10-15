import threading

from .simulation_request import parse_simulation_request
from src.network_simulation import NetworkSimulation


class NetworkAPIHandler:
    def __init__(self):
        self.ns = NetworkSimulation()
        self.is_starting = False
        self.is_started = False

    def cleanup(self):
        try:
            self.ns.cleanup()
            return {"state": 1, "msg": "环境清理成功"}
        except RuntimeError as e:
            return {"state": 0, "msg": f"错误详情：{e}"}

    def start_simulation(self, data, use_thread=True):
        try:
            if self.is_starting or self.is_started:
                return {"state": 0, "msg": '环境已启动或在启动中，请勿重复启动'}

            request = parse_simulation_request(data)

            if use_thread:
                thread = threading.Thread(target=self.start_in_thread,
                                          args=(request,))
                thread.start()
                return {"state": 1, "msg": "开始启动环境"}
            else:
                self.start_in_thread(request)
                return self.get_status()
        except ValueError as exc:
            return {"state": 0, "msg": f"请求参数错误：{exc}"}
        except RuntimeError as e:
            return {"state": 0, "msg": f"错误详情：{e}"}

    def start_in_thread(self, request):
        self.is_starting = True
        self.ns.cleanup()

        if request.topology_type == 'static':
            self.ns.create_custom_topology(
                nodes=request.static_topology['nodes'],
                edges=request.static_topology['edges'],
            )
        else:
            self.ns.create_random_nodes(request.node_count)

        if request.lisp_mode == 'simulation':
            self.ns.create_lisp_topology(num_xtr=request.xtr_count, num_msmr=request.ms_count)
        elif request.lisp_mode == 'real':
            self.ns.create_lisp_macvlan(num_msmr=1)

        self.ns.display_network_topology()
        self.ns.start_simulation()

        if request.use_static_routes:
            self.ns.create_static_routes()

        self.is_started = True
        self.is_starting = False

    def stop_simulation(self):
        try:
            self.ns.stop_simulation()
            self.is_started = False
            return {"state": 1, "msg": "环境终止成功"}
        except RuntimeError as e:
            return {"state": 0, "msg": f"错误详情：{e}"}

    def get_status(self):
        try:
            if self.is_started:
                return {"state": 1, "msg": "环境状态获取成功",
                        "topo": self.ns.get_topo(),
                        "container": self.ns.get_status()}
            elif self.is_starting:
                return {"state": 0, "msg": "环境正在启动中，请稍候"}
            else:
                return {"state": 0, "msg": "环境未启动"}
        except RuntimeError as e:
            return {"state": 0, "msg": f"错误详情：{e}"}

    def get_node_ipaddr(self, node_name):
        try:
            node = next((node for node in self.ns.nodes if node.name == node_name), None)
            if node:
                return {"state": 1, "msg": "容器ip地址获取成功", "data": node.get_ip_addr()}
            else:
                return {"state": 0, "msg": f'未找到名为 {node_name} 的节点'}
        except Exception as e:
            return {"state": 0, "msg": f"错误详情: {str(e)}"}

    def get_node_iproute(self, node_name):
        try:
            node = next((node for node in self.ns.nodes if node.name == node_name), None)
            if node:
                return {"state": 1, "msg": "容器ip路由获取成功", "data": node.get_ip_route()}
            else:
                return {"state": 0, "msg": f'未找到名为 {node_name} 的节点'}
        except Exception as e:
            return {"state": 0, "msg": f"错误详情: {str(e)}"}

    def get_pair_delay(self, src_node_name, dst_node_name):
        try:
            if not self.is_started:
                return {"state": 0, "msg": '环境未启动，请启动环境后获取'}
            res = self.ns.get_pair_delay_by_name(src_node_name, dst_node_name)
            if res:
                return {"state": 1, "msg": "链路延迟获取成功", "data": res}
            else:
                return {"state": 0, "msg": f'未找到名为 {src_node_name} 或 {dst_node_name} 的节点'}
        except Exception as e:
            return {"state": 0, "msg": f"错误详情: {str(e)}"}

    def set_tc_on_edges(self, data):
        try:
            edges = data.get('edges')
            delay = data.get('delay')
            jitter = data.get('jitter')
            loss = data.get('loss')
            max_queue_size = data.get('max_queue_size')
            self.ns.apply_tc_on_edges(edges, delay=delay, jitter=jitter, loss=loss, max_queue_size=max_queue_size)
            return {"state": 1, "msg": "tc规则配置成功"}
        except Exception as e:
            return {"state": 0, "msg": f"错误详情: {str(e)}"}
