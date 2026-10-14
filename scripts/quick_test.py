import argparse
from collections import Counter

from src.network_simulation import NetworkSimulation

DEFAULT_XTR_EDGES = (("node_1", "xtr_1"), ("node_3", "xtr_2"))


def parse_xtr_edge(value):
    if ":" in value:
        left, right = value.split(":", 1)
    elif "," in value:
        left, right = value.split(",", 1)
    else:
        raise argparse.ArgumentTypeError("expected ROUTER:XTR or ROUTER,XTR")
    router = left.strip()
    xtr = right.strip()
    if not router or not xtr:
        raise argparse.ArgumentTypeError("router and xTR names must not be empty")
    return [router, xtr]


def validate_xtr_edges(args):
    router_names = {f"node_{index + 1}" for index in range(args.nodes)}
    xtr_counts = Counter(xtr for _router, xtr in args.xtr_edge)
    duplicate_xtrs = sorted(xtr for xtr, count in xtr_counts.items() if count > 1)
    if duplicate_xtrs:
        raise argparse.ArgumentTypeError(
            f"--xtr-edge contains duplicate xTR names: {', '.join(duplicate_xtrs)}"
        )

    for router, xtr in args.xtr_edge:
        if router not in router_names:
            raise argparse.ArgumentTypeError(
                f"--xtr-edge router {router!r} is outside the generated node_1..node_{args.nodes} topology"
            )
        if xtr in router_names:
            raise argparse.ArgumentTypeError(
                f"--xtr-edge xTR name {xtr!r} conflicts with a generated router name"
            )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run a small Docker topology smoke test.")
    parser.add_argument(
        "--nodes",
        type=int,
        default=5,
        help="number of circle-router nodes to create",
    )
    parser.add_argument(
        "--msmr",
        type=int,
        default=1,
        help="number of MSMR nodes in the LISP topology",
    )
    parser.add_argument(
        "--xtr-edge",
        action="append",
        type=parse_xtr_edge,
        default=None,
        metavar="ROUTER:XTR",
        help="router-to-xTR edge; repeat for multiple edges",
    )
    args = parser.parse_args(argv)
    if args.nodes < 3:
        parser.error("--nodes must be at least 3")
    if args.msmr < 1:
        parser.error("--msmr must be at least 1")
    if args.xtr_edge is None:
        args.xtr_edge = [list(edge) for edge in DEFAULT_XTR_EDGES]
    try:
        validate_xtr_edges(args)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
    return args


def main(argv=None):
    args = parse_args(argv)
    network_simulation = NetworkSimulation()
    network_simulation.cleanup()
    network_simulation.create_circle_nodes(args.nodes)
    network_simulation.create_lisp_topology(
        xtr_edges=args.xtr_edge,
        num_msmr=args.msmr,
    )
    network_simulation.display_network_topology()
    network_simulation.start_simulation()


if __name__ == "__main__":
    main()
