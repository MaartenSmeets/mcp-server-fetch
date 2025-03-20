from .server import serve


def main():
    """MCP Fetch Server - HTTP fetching functionality for MCP"""
    import argparse
    import asyncio
    import logging

    parser = argparse.ArgumentParser(
        description="give a model the ability to make web requests"
    )
    parser.add_argument("--user-agent", type=str, help="Custom User-Agent string")
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level"
    )
    parser.add_argument(
        "--log-file",
        type=str,
        help="Log to specified file instead of stderr"
    )

    args = parser.parse_args()
    
    # Configure logging if log file is specified
    if args.log_file:
        logging.basicConfig(
            level=getattr(logging, args.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename=args.log_file,
            filemode='a'
        )
        print(f"Logging to file: {args.log_file} at level {args.log_level}")
    
    asyncio.run(serve(args.user_agent, args.log_level))


if __name__ == "__main__":
    main()