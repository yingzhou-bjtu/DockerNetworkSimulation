import threading

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

            print(data)
            topology_type = data.get('topology_type')  # 'static' 或 'random'
            static_topology = data.get('static_topology') if topology_type == 'static' else None
            node_count = data.get('node_count') if topology_type == 'random' else None
            lisp_mode = data.get('lisp_mode', 'none')  # 'simulation' 或 'real' 或 'none'
            xtr_count = data.get('xtr_count') if lisp_mode == 'simulation' else None
            ms_count = data.get('ms_count') if lisp_mode == 'simulation' else None
            use_static_routes = data.get('use_static_routes', False)

            # 参数验证
            if topology_type not in ['static', 'random']:
                return {"state": 0, "msg": "必须指定有效的拓扑类型：'static' 或 'random'"}
            if topology_type == 'static' and not static_topology:
                return {"state": 0, "msg": "静态拓扑需要提供拓扑配置"}
            if topology_type == 'random' and not node_count:
                return {"state": 0, "msg": "随机拓扑需要提供节点数量"}
            if lisp_mode == 'simulation' and (xtr_count is None or ms_count is None):
                return {"state": 0, "msg": "启用LISP模拟模式时必须提供xTR和MS的数量"}
            if use_static_routes and not topology_type:
                return {"state": 0, "msg": "必须在启用拓扑后才能启用静态路由"}

            if use_thread:
                thread = threading.Thread(target=self.start_in_thread,
                                          args=(topology_type, static_topology, node_count,
                                                lisp_mode, xtr_count, ms_count, use_static_routes))
                thread.start()
                return {
                    "state": 1,
                    "msg": "开始启动环境"
                }
            else:
                self.start_in_thread(topology_type, static_topology, node_count,
                                     lisp_mode, xtr_count, ms_count, use_static_routes)
                return self.get_status()
        except RuntimeError as e:
            return {"state": 0, "msg": f"错误详情：{e}"}

    def start_in_thread(self, topology_type, static_topology, node_count,
                        lisp_mode, xtr_count, ms_count, use_static_routes):
        self.is_starting = True
        self.ns.cleanup()

        if topology_type == 'static':  # 使用静态拓扑
            self.ns.create_custom_topology(nodes=static_topology['nodes'], edges=static_topology['edges'])
        elif topology_type == 'random':  # 使用随机拓扑
            self.ns.create_random_nodes(node_count)
        if lisp_mode == 'simulation':  # 使用模拟LISP节点，包含客户端
            self.ns.create_lisp_topology(num_xtr=xtr_count, num_msmr=ms_count)
        elif lisp_mode == 'real':  # 使用macvlan模式LISP节点
            self.ns.create_lisp_macvlan(num_msmr=1)

        self.ns.display_network_topology()
        self.ns.start_simulation()

        if use_static_routes:  # 使用静态路由
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
            print(loss)
            print(type(loss))
            max_queue_size = data.get('max_queue_size')
            self.ns.apply_tc_on_edges(edges, delay=delay, jitter=jitter, loss=loss, max_queue_size=max_queue_size)
            return {"state": 1, "msg": "tc规则配置成功"}
        except Exception as e:
            return {"state": 0, "msg": f"错误详情: {str(e)}"}
