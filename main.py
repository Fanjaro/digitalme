#!/usr/bin/env python3
"""DigitalMe multi-agent system CLI entry point."""
import argparse
import logging
import sys

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s: %(message)s")


def run_graph(sample_id: str):
    """Run the full multi-agent graph for a given sample ID."""
    from graph import build_graph

    print(f"Starting DigitalMe multi-agent pipeline for sample: {sample_id}")
    print("=" * 60)

    graph = build_graph()
    result = graph.invoke({
        "user_sample_id": sample_id,
        "user_meta": None,
        "target_dimensions": [],
        "dimension_results": [],
        "synthesized_report": None,
    })

    report = result.get("synthesized_report", "")
    if report:
        print("\n" + "=" * 60)
        print(report)
    else:
        print("\nNo report generated.")

    return result


def run_interactive():
    """Run interactive mode."""
    print("DigitalMe Multi-Agent Health Analysis System")
    print("=" * 60)
    print("输入样本ID开始分析，输入 'quit' 退出\n")

    while True:
        try:
            sample_id = input("样本ID> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n退出")
            break

        if not sample_id or sample_id.lower() in ("quit", "exit", "q"):
            break

        try:
            run_graph(sample_id)
        except Exception as e:
            print(f"Error: {e}")
        print()


def list_dimensions():
    """List all registered dimensions."""
    from dimensions import get_registry, get_prefix_map

    reg = get_registry()
    pm = get_prefix_map()

    print(f"Registered dimensions: {len(reg)}")
    print(f"{'Key':10s} {'Display Name':16s} {'Prefixes':12s} {'API':5s} {'Structure Type'}")
    print("-" * 75)
    for k, v in sorted(reg.items()):
        cfg = v["config"]
        prefixes = ", ".join(cfg["sample_id"]["prefixes"])
        api = cfg["api"]["version"]
        st = cfg["data_extraction"]["structure_type"]
        name = cfg["dimension"]["display_name"]
        print(f"{k:10s} {name:16s} {prefixes:12s} {api:5s} {st}")


def main():
    parser = argparse.ArgumentParser(description="DigitalMe Multi-Agent Health Analysis")
    parser.add_argument("--sample-id", "-s", help="Sample ID to analyze")
    parser.add_argument("--list-dimensions", "-l", action="store_true", help="List registered dimensions")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    args = parser.parse_args()

    if args.list_dimensions:
        list_dimensions()
    elif args.sample_id:
        run_graph(args.sample_id)
    elif args.interactive:
        run_interactive()
    else:
        # Default to interactive if no args
        if sys.stdin.isatty():
            run_interactive()
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
