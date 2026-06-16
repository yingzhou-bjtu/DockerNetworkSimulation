
# 接口文档

本文档介绍了使用相同底层 API 处理程序实现的两个接口：

- RESTful Flask API 
- RabbitMQ 消息队列接口

两者暴露了相同的功能。

本文档的详细内容有待完善。

---

## Flask RESTful API

Flask API 提供了通过 HTTP 方法管理网络模拟的接口。

### 基础 URL:
```
http://<主机>:<端口>
```

### 接口列表：

#### 1. **启动模拟**

- **接口路径**: `/start`

- **请求方法**: `POST`

- **描述**: 使用提供的配置启动网络模拟。

- **请求体**（JSON格式）:
    
    ```json
    {
        "topology_type": "static", // 使用static或random，static需提供static_topology，random需提供node_count
        "static_topology": {
            "nodes": [
                {
                    "name": "node_1",
                    "type": "Router",
                    "coordinates": {
                        "latitude": 39.906217,
                        "longitude": 116.3912757
                    }
                },
                {
                    "name": "node_2",
                    "type": "Router",
                    "coordinates": {
                        "latitude": 31.2304,
                        "longitude": 121.4737
                    }
                },
                {
                    "name": "node_3",
                    "type": "Router",
                    "coordinates": {
                        "latitude": 23.06,
                        "longitude": 113.15
                    }
                },
                {
                    "name": "node_4",
                    "type": "Router",
                    "coordinates": {
                        "latitude": 22.5455,
                        "longitude": 114.0683
                    }
                }
            ], //仅static模式需提供，节点列表
            "edges": [
                [
                    "node_1",
                    "node_2"
                ],
                [
                    "node_2",
                    "node_3"
                ],
                [
                    "node_3",
                    "node_4"
                ]
            ] //仅static模式需提供，边关系
        },
        "node_count": 10, // 仅random模式需提供，随机路由节点数量
        "lisp_mode": "simulation", // 可选：simulation、real、none, simulation使用模拟客户端，real模式使用网卡直通，none不启用lisp节点（双方调试使用simulation，最终联调使用real）
        "xtr_count": 2, // 仅simulation模式需提供，需要提供xTR数量（默认为2即可）
        "ms_count": 1, // 仅simulation模式需提供，需要提供MS数量（默认为1即可）
        "use_static_routes": false // 是否使用静态路由（默认为false即可）
    }
    ```
    
- **响应**（JSON格式）:
    
    ```json
    {
      "state": 1,  // 1 表示成功, 0 表示失败
      "msg": "开始启动环境"
    }
    ```

#### 2. **停止模拟**

- **接口路径**: `/stop`
- **请求方法**: `POST`
- **描述**: 停止当前正在运行的网络模拟。
- **响应**（JSON格式）:
    ```json
    {
      "state": 1,  // 1 表示成功, 0 表示失败
      "msg": "环境终止成功"
    }
    ```

#### 3. **获取状态**

- **接口路径**: `/status`
- **请求方法**: `GET`
- **描述**: 获取当前模拟的状态。
- **成功响应**（JSON格式）:
    ```json
    {
        "container": {  //容器运行状态
            "Client1": "running",
            "Client2": "running",
            "MSMR1": "running",
            "node_1": "running",
            "node_2": "running",
            "node_3": "running",
            "node_4": "running",
            "xTR1": "running",
            "xTR2": "running"
        },
        "msg": "环境状态获取成功",
        "state": 1,
        "topo": {  //拓扑状态
            "edges": [
                [
                    "node_1",
                    "node_2"
                ],
                [
                    "node_1",
                    "xTR1"
                ],
                [
                    "node_2",
                    "node_3"
                ],
                [
                    "node_2",
                    "xTR2"
                ],
                [
                    "node_3",
                    "node_4"
                ],
                [
                    "node_3",
                    "MSMR1"
                ],
                [
                    "xTR1",
                    "Client1"
                ],
                [
                    "xTR2",
                    "Client2"
                ]
            ],
            "nodes": [
                {
                    "coordinates": {
                        "latitude": 39.906217,
                        "longitude": 116.3912757
                    },
                    "name": "node_1",
                    "type": "Router"
                },
                {
                    "coordinates": {
                        "latitude": 31.2304,
                        "longitude": 121.4737
                    },
                    "name": "node_2",
                    "type": "Router"
                },
                {
                    "coordinates": {
                        "latitude": 23.06,
                        "longitude": 113.15
                    },
                    "name": "node_3",
                    "type": "Router"
                },
                {
                    "coordinates": {
                        "latitude": 22.5455,
                        "longitude": 114.0683
                    },
                    "name": "node_4",
                    "type": "Router"
                },
                {
                    "coordinates": {
                        "latitude": 0.0,
                        "longitude": 0.0
                    },
                    "name": "xTR1",
                    "type": "xTR"
                },
                {
                    "coordinates": {
                        "latitude": 0.0,
                        "longitude": 0.0
                    },
                    "name": "xTR2",
                    "type": "xTR"
                },
                {
                    "coordinates": {
                        "latitude": 0.0,
                        "longitude": 0.0
                    },
                    "name": "MSMR1",
                    "type": "MSMR"
                },
                {
                    "coordinates": {
                        "latitude": 0.0,
                        "longitude": 0.0
                    },
                    "name": "Client1",
                    "type": "Client"
                },
                {
                    "coordinates": {
                        "latitude": 0.0,
                        "longitude": 0.0
                    },
                    "name": "Client2",
                    "type": "Client"
                }
            ]
        }
    }
    
- **失败响应**（JSON格式）:
  ```json
  {
      "msg": "环境正在启动中，请稍候",
      "state": 0
  }
  ```

#### 4. **获取节点IP地址**

- **接口路径**: `/node/ipaddr`
- **请求方法**: `GET`
- **描述**: 获取指定节点的IP地址。
- **请求体**（JSON格式）:
    ```json
    {
      "node_name": "node_1"
    }
    ```
- **响应**（JSON格式）:
    ```json
  {
      "data": {
          "eth1@if1369": {
              "inet": [
                  "10.10.0.44/24"
              ],
              "inet6": []
          },
          "eth2@if1383": {
              "inet": [
                  "10.10.3.71/24"
              ],
              "inet6": []
          },
          "eth3@if1389": {
              "inet": [
                  "10.10.5.76/24"
              ],
              "inet6": []
          },
          "lo": {
              "inet": [
                  "127.0.0.1/8"
              ],
              "inet6": [
                  "::1/128"
              ]
          }
      },
      "msg": "容器ip地址获取成功",
      "state": 1
  }
  ```

#### 5. **获取节点IP路由**

- **接口路径**: `/node/iproute`
- **请求方法**: `GET`
- **描述**: 获取指定节点的IP路由表。
- **请求体**（JSON格式）:

    ```json
    {
      "node_name": "node_1"
    }
    ```

- **响应**（JSON格式）:
    ```json
  {
      "data": [
          {
              "destination": "10.10.0.0/24",
              "interface": "eth1",
              "proto": "kernel",
              "scope": "link",
              "src": "10.10.0.44"
          },
          {
              "destination": "10.10.0.213",
              "gateway": "10.10.0.213",
              "interface": "eth1"
          },
          {
              "destination": "10.10.1.0/24",
              "gateway": "10.10.0.213",
              "interface": "eth1"
          },
          {
              "destination": "10.10.1.16",
              "gateway": "10.10.0.213",
              "interface": "eth1"
          },
          {
              "destination": "10.10.2.0/24",
              "gateway": "10.10.0.213",
              "interface": "eth1"
          },
          {
              "destination": "10.10.2.214",
              "gateway": "10.10.0.213",
              "interface": "eth1"
          },
          {
              "destination": "10.10.3.0/24",
              "interface": "eth2",
              "proto": "kernel",
              "scope": "link",
              "src": "10.10.3.71"
          },
          {
              "destination": "10.10.3.81",
              "gateway": "10.10.3.81",
              "interface": "eth2"
          },
          {
              "destination": "10.10.4.0/24",
              "gateway": "10.10.0.213",
              "interface": "eth1"
          },
          {
              "destination": "10.10.4.26",
              "gateway": "10.10.0.213",
              "interface": "eth1"
          },
          {
              "destination": "10.10.5.0/24",
              "interface": "eth3",
              "proto": "kernel",
              "scope": "link",
              "src": "10.10.5.76"
          },
          {
              "destination": "10.10.5.85",
              "gateway": "10.10.5.85",
              "interface": "eth3"
          },
          {
              "destination": "10.10.6.0/24",
              "gateway": "10.10.3.81",
              "interface": "eth2"
          },
          {
              "destination": "10.10.7.0/24",
              "gateway": "10.10.0.213",
              "interface": "eth1"
          }
      ],
      "msg": "容器ip路由获取成功",
      "state": 1
  }
  ```

#### 6. **获取节点间延迟**

- **接口路径**: `/get-delay`
- **请求方法**: `GET`
- **描述**: 获取两个节点之间的延迟。
- **请求体**（JSON格式）:
    ```json
    {
      "src_node_name": "node1",
      "dst_node_name": "node2"
    }
    ```
- **响应**（JSON格式）:
    ```json
  {
      "data": {
          "avg_delay": 0.09266666666666667,
          "loss_rate": 0.0,
          "max_delay": 0.137,
          "mdev": 0.03141478774222244,
          "min_delay": 0.068,
          "pkg_count": 3
      },
      "msg": "链路延迟获取成功",
      "state": 1
  }
  ```

#### 7. **设置节点延迟**

- **接口路径**: `/set_delay`
- **请求方法**: `POST`
- **描述**: 在特定的网络边上设置流量控制（tc）规则，以模拟网络条件（如延迟）。
- **请求体**（JSON格式）:
    ```json
    {
      "edges": [["node_1", "node_2"], ["node_3", "node_4"]], //下列设置项设置哪项就加入哪个键，不设置可不添加
      "delay": "100ms",  //非必须设置
      "jitter": "10ms",  //非必须设置
      "loss": 20.0,  //非必须设置，浮点数
      "max_queue_size": 1000  //非必须设置
    }
    ```
- **响应**（JSON格式）:
    ```json
    {
      "state": 1,
      "msg": "tc规则配置成功"
    }
    ```

---

## RabbitMQ 接口

RabbitMQ 消息队列接口提供了与 REST API 相同的功能，但通过消息代理进行通信。

### 配置：
- **交换器**: `<exchange_name>`
- **队列**:
  - **输入队列**: `<inbound_queue>`
  - **输出队列**: `<outbound_queue>`

### 消息格式：

每个发送到输入队列的请求应包含以下结构：

```json
{
  "link": "/start",  // 对应 REST API 的路径
  // 其他请求所需的参数
}
```

### RabbitMQ 请求-响应映射：

#### 1. **启动模拟**

注意：该接口与对应restful接口有部分区别，在该接口中，程序将不使用后台线程，在执行完毕后（可能消耗较长时间）直接返回当前状态信息。

- **请求**:
  
    ```json
    {
        "link": "/start",
        "topology_type": "static", // 使用static或random，static需提供static_topology，random需提供node_count
        "static_topology": {
            "nodes": [
                {
                    "name": "node_1",
                    "type": "router",
                    "coordinates": {
                        "latitude": 39.906217,
                        "longitude": 116.3912757
                    }
                },
                {
                    "name": "node_2",
                    "type": "router",
                    "coordinates": {
                        "latitude": 31.2304,
                        "longitude": 121.4737
                    }
                },
                {
                    "name": "node_3",
                    "type": "router",
                    "coordinates": {
                        "latitude": 23.06,
                        "longitude": 113.15
                    }
                },
                {
                    "name": "node_4",
                    "type": "router",
                    "coordinates": {
                        "latitude": 22.5455,
                        "longitude": 114.0683
                    }
                }
            ], //仅static模式需提供，节点列表
            "edges": [
                [
                    "node_1",
                    "node_2"
                ],
                [
                    "node_2",
                    "node_3"
                ],
                [
                    "node_3",
                    "node_4"
                ]
            ] //仅static模式需提供，边关系
        },
        "node_count": 10, // 仅random模式需提供，随机路由节点数量
        "lisp_mode": "simulation", // 可选：simulation、real、none, simulation使用模拟客户端，real模式使用网卡直通，none不启用lisp节点（双方调试使用simulation，最终联调使用real）
        "xtr_count": 2, // 仅simulation模式需提供，需要提供xTR数量（默认为2即可）
        "ms_count": 1, // 仅simulation模式需提供，需要提供MS数量（默认为1即可）
        "use_static_routes": false // 是否使用静态路由（默认为false即可）
    }
    ```
- **响应**:
    ```json
    {
        "container": {  //容器运行状态
            "Client1": "running",
            "Client2": "running",
            "MSMR1": "running",
            "node_1": "running",
            "node_2": "running",
            "node_3": "running",
            "node_4": "running",
            "xTR1": "running",
            "xTR2": "running"
        },
        "msg": "环境状态获取成功",
        "state": 1,
        "topo": {  //拓扑状态
            "edges": [
                [
                    "node_1",
                    "node_2"
                ],
                [
                    "node_1",
                    "xTR1"
                ],
                [
                    "node_2",
                    "node_3"
                ],
                [
                    "node_2",
                    "xTR2"
                ],
                [
                    "node_3",
                    "node_4"
                ],
                [
                    "node_3",
                    "MSMR1"
                ],
                [
                    "xTR1",
                    "Client1"
                ],
                [
                    "xTR2",
                    "Client2"
                ]
            ],
            "nodes": [
                {
                    "coordinates": {
                        "latitude": 39.906217,
                        "longitude": 116.3912757
                    },
                    "name": "node_1",
                    "type": "Router"
                },
                {
                    "coordinates": {
                        "latitude": 31.2304,
                        "longitude": 121.4737
                    },
                    "name": "node_2",
                    "type": "Router"
                },
                {
                    "coordinates": {
                        "latitude": 23.06,
                        "longitude": 113.15
                    },
                    "name": "node_3",
                    "type": "Router"
                },
                {
                    "coordinates": {
                        "latitude": 22.5455,
                        "longitude": 114.0683
                    },
                    "name": "node_4",
                    "type": "Router"
                },
                {
                    "coordinates": {
                        "latitude": 0.0,
                        "longitude": 0.0
                    },
                    "name": "xTR1",
                    "type": "xTR"
                },
                {
                    "coordinates": {
                        "latitude": 0.0,
                        "longitude": 0.0
                    },
                    "name": "xTR2",
                    "type": "xTR"
                },
                {
                    "coordinates": {
                        "latitude": 0.0,
                        "longitude": 0.0
                    },
                    "name": "MSMR1",
                    "type": "MSMR"
                },
                {
                    "coordinates": {
                        "latitude": 0.0,
                        "longitude": 0.0
                    },
                    "name": "Client1",
                    "type": "Client"
                },
                {
                    "coordinates": {
                        "latitude": 0.0,
                        "longitude": 0.0
                    },
                    "name": "Client2",
                    "type": "Client"
                }
            ]
        }
    }
    ```

#### 2. **停止模拟**
- **请求**:
    ```json
    {
      "link": "/stop"
    }
    ```
- **响应**:
    ```json
    {
      "state": 1,
      "msg": "环境终止成功"
    }
    ```

#### 3. **获取状态**
- **请求**:
    ```json
    {
      "link": "/status"
    }
    ```
- **响应**:
  
    ```json
    {
        "container": {  //容器运行状态
            "Client1": "running",
            "Client2": "running",
            "MSMR1": "running",
            "node_1": "running",
            "node_2": "running",
            "node_3": "running",
            "node_4": "running",
            "xTR1": "running",
            "xTR2": "running"
        },
        "msg": "环境状态获取成功",
        "state": 1,
        "topo": {  //拓扑状态
            "edges": [
                [
                    "node_1",
                    "node_2"
                ],
                [
                    "node_1",
                    "xTR1"
                ],
                [
                    "node_2",
                    "node_3"
                ],
                [
                    "node_2",
                    "xTR2"
                ],
                [
                    "node_3",
                    "node_4"
                ],
                [
                    "node_3",
                    "MSMR1"
                ],
                [
                    "xTR1",
                    "Client1"
                ],
                [
                    "xTR2",
                    "Client2"
                ]
            ],
            "nodes": [
                {
                    "coordinates": {
                        "latitude": 39.906217,
                        "longitude": 116.3912757
                    },
                    "name": "node_1",
                    "type": "Router"
                },
                {
                    "coordinates": {
                        "latitude": 31.2304,
                        "longitude": 121.4737
                    },
                    "name": "node_2",
                    "type": "Router"
                },
                {
                    "coordinates": {
                        "latitude": 23.06,
                        "longitude": 113.15
                    },
                    "name": "node_3",
                    "type": "Router"
                },
                {
                    "coordinates": {
                        "latitude": 22.5455,
                        "longitude": 114.0683
                    },
                    "name": "node_4",
                    "type": "Router"
                },
                {
                    "coordinates": {
                        "latitude": 0.0,
                        "longitude": 0.0
                    },
                    "name": "xTR1",
                    "type": "xTR"
                },
                {
                    "coordinates": {
                        "latitude": 0.0,
                        "longitude": 0.0
                    },
                    "name": "xTR2",
                    "type": "xTR"
                },
                {
                    "coordinates": {
                        "latitude": 0.0,
                        "longitude": 0.0
                    },
                    "name": "MSMR1",
                    "type": "MSMR"
                },
                {
                    "coordinates": {
                        "latitude": 0.0,
                        "longitude": 0.0
                    },
                    "name": "Client1",
                    "type": "Client"
                },
                {
                    "coordinates": {
                        "latitude": 0.0,
                        "longitude": 0.0
                    },
                    "name": "Client2",
                    "type": "Client"
                }
            ]
        }
    }
    ```

#### 4. **获取节点IP地址**
- **请求**:
    ```json
    {
      "link": "/node/ipaddr",
      "node_name": "node_1"
    }
    ```
- **响应**:
    ```json
    {
        "data": {
            "eth1@if1369": {
                "inet": [
                    "10.10.0.44/24"
                ],
                "inet6": []
            },
            "eth2@if1383": {
                "inet": [
                    "10.10.3.71/24"
                ],
                "inet6": []
            },
            "eth3@if1389": {
                "inet": [
                    "10.10.5.76/24"
                ],
                "inet6": []
            },
            "lo": {
                "inet": [
                    "127.0.0.1/8"
                ],
                "inet6": [
                    "::1/128"
                ]
            }
        },
        "msg": "容器ip地址获取成功",
        "state": 1
    }
    ```

#### 5. **获取节点IP路由**
- **请求**:
    ```json
    {
      "link": "/node/iproute",
      "node_name": "node_1"
    }
    ```
- **响应**:
    ```json
    {
        "data": [
            {
                "destination": "10.10.0.0/24",
                "interface": "eth1",
                "proto": "kernel",
                "scope": "link",
                "src": "10.10.0.44"
            },
            {
                "destination": "10.10.0.213",
                "gateway": "10.10.0.213",
                "interface": "eth1"
            },
            {
                "destination": "10.10.1.0/24",
                "gateway": "10.10.0.213",
                "interface": "eth1"
            },
            {
                "destination": "10.10.1.16",
                "gateway": "10.10.0.213",
                "interface": "eth1"
            },
            {
                "destination": "10.10.2.0/24",
                "gateway": "10.10.0.213",
                "interface": "eth1"
            },
            {
                "destination": "10.10.2.214",
                "gateway": "10.10.0.213",
                "interface": "eth1"
            },
            {
                "destination": "10.10.3.0/24",
                "interface": "eth2",
                "proto": "kernel",
                "scope": "link",
                "src": "10.10.3.71"
            },
            {
                "destination": "10.10.3.81",
                "gateway": "10.10.3.81",
                "interface": "eth2"
            },
            {
                "destination": "10.10.4.0/24",
                "gateway": "10.10.0.213",
                "interface": "eth1"
            },
            {
                "destination": "10.10.4.26",
                "gateway": "10.10.0.213",
                "interface": "eth1"
            },
            {
                "destination": "10.10.5.0/24",
                "interface": "eth3",
                "proto": "kernel",
                "scope": "link",
                "src": "10.10.5.76"
            },
            {
                "destination": "10.10.5.85",
                "gateway": "10.10.5.85",
                "interface": "eth3"
            },
            {
                "destination": "10.10.6.0/24",
                "gateway": "10.10.3.81",
                "interface": "eth2"
            },
            {
                "destination": "10.10.7.0/24",
                "gateway": "10.10.0.213",
                "interface": "eth1"
            }
        ],
        "msg": "容器ip路由获取成功",
        "state": 1
    }
    ```

#### 6. **获取节点间延迟**
- **请求**:
    ```json
    {
      "link": "/get-delay",
      "src_node_name": "node_1",
      "dst_node_name": "node_2"
    }
    ```
- **响应**:
    ```json
    {
        "data": {
            "avg_delay": 0.09266666666666667,
            "loss_rate": 0.0,
            "max_delay": 0.137,
            "mdev": 0.03141478774222244,
            "min_delay": 0.068,
            "pkg_count": 3
        },
        "msg": "链路延迟获取成功",
        "state": 1
    }
    ```

#### 7. **设置延迟**
- **请求**:
    
    ```json
    {
      "link": "/set_delay",
      "edges": [["node_1", "node_2"], ["node_3", "node_4"]], //下列设置项设置哪项就加入哪个键，不设置可不添加
      "delay": "100ms",  //非必须设置
      "jitter": "10ms",  //非必须设置
      "loss": 20.0,  //非必须设置，浮点数
      "max_queue_size": 1000  //非必须设置
    }
    ```
- **响应**:
    ```json
    {
      "state": 1,
      "msg": "tc规则配置成功"
    }
    ```

