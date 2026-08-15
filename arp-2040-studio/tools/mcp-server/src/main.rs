use arp_2040_mcp::*;
use clap::Parser;

fn main() {
    let args = Args::parse();
    match args.transport {
        Transport::Stdio => run_stdio().ok(),
        Transport::Tcp => run_tcp(args.tcp_port, &args.tcp_bind).ok(),
    };
}
