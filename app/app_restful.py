from flask import Flask, jsonify, request
from .network_api_handler import NetworkAPIHandler


def create_app(network_handler):
    """Flask应用工厂函数，用于创建应用实例"""
    app = Flask(__name__)

    @app.route('/cleanup', methods=['POST'])
    def cleanup():
        result = network_handler.cleanup()
        return jsonify(result)

    @app.route('/start', methods=['POST'])
    def start_simulation():
        js = request.get_json(silent=True)
        result = network_handler.start_simulation(js)
        return jsonify(result)

    @app.route('/stop', methods=['POST'])
    def stop_simulation():
        result = network_handler.stop_simulation()
        return jsonify(result)

    @app.route('/status', methods=['GET'])
    def get_status():
        result = network_handler.get_status()
        return jsonify(result)

    @app.route('/node/ipaddr', methods=['GET'])
    def get_node_ipaddr():
        js = request.get_json(silent=True)
        node_name = js.get('node_name') if js else None
        result = network_handler.get_node_ipaddr(node_name)
        return jsonify(result)

    @app.route('/node/iproute', methods=['GET'])
    def get_node_iproute():
        js = request.get_json(silent=True)
        node_name = js.get('node_name') if js else None
        result = network_handler.get_node_iproute(node_name)
        return jsonify(result)

    @app.route('/get-delay', methods=['GET'])
    def get_pair_delay():
        js = request.get_json(silent=True)
        src_node_name = js.get('src_node_name') if js else None
        dst_node_name = js.get('dst_node_name') if js else None
        result = network_handler.get_pair_delay_by_name(src_node_name, dst_node_name)
        return jsonify(result)

    @app.route('/set_delay', methods=['POST'])
    def set_delay():
        js = request.get_json(silent=True)
        result = network_handler.set_tc_on_edges(js)
        return jsonify(result)

    return app


def start_flask_app(network_handler: NetworkAPIHandler, flask_config):
    app = create_app(network_handler)
    print(f'-> Flask API已启动： http://{flask_config["host"]}:{flask_config["port"]}，调试模式：{flask_config["debug"]}')
    app.run(host=flask_config['host'], port=flask_config['port'], debug=flask_config['debug'])
