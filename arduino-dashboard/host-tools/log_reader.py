"""
Arduino Log Reader
Host-side tool to retrieve buffered boot/self-test logs from Arduino firmware
via the DUMP command, bypassing serial monitor race conditions.
"""
import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent / "host-tools"))

from transport.serial_transport import SerialTransport

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("log-reader")

async def read_boot_log(port: str = "COM15", baudrate: int = 921600, output_path: Path = None) -> str:
    """
    Read boot/self-test log from Arduino via DUMP command.
    
    Args:
        port: Serial port
        baudrate: Baud rate
        output_path: Optional path to save log file
    
    Returns:
        Log content as string
    """
    transport = SerialTransport(port=port, baudrate=baudrate)
    try:
        await transport.connect()
        logger.info(f"Connected to {port}, sending DUMP command...")
        
        # Wait for board to settle
        await asyncio.sleep(0.5)
        
        # Send DUMP command
        await transport.send_command("DUMP")
        
        # Read response with timeout
        response = await asyncio.wait_for(transport.read_line(), timeout=3.0)
        if not response:
            logger.warning("No response received")
            return ""
        
        # Read the dump content
        log_lines = []
        start_marker = "[DUMP]"
        end_marker = "[END DUMP]"
        in_dump = False
        
        async def read_with_timeout():
            nonlocal response
            while True:
                response = await transport.read_line()
                if response is None:
                    await asyncio.sleep(0.01)
                    continue
                log_lines.append(response)
                if end_marker in response:
                    break
        
        try:
            await asyncio.wait_for(read_with_timeout(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Timeout reading dump")
        
        # Extract content between markers
        content = "\n".join(log_lines)
        if start_marker in content and end_marker in content:
            start_idx = content.index(start_marker) + len(start_marker)
            end_idx = content.index(end_marker)
            content = content[start_idx:end_idx].strip()
        
        # Save to file if requested
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")
            logger.info(f"Log saved to {output_path}")
        
        return content
        
    finally:
        await transport.disconnect()

async def tail_live_log(port: str = "COM15", baudrate: int = 921600, duration_s: int = 60):
    """
    Tail live log from Arduino for specified duration.
    
    Args:
        port: Serial port
        baudrate: Baud rate
        duration_s: Duration to tail in seconds
    """
    transport = SerialTransport(port=port, baudrate=baudrate)
    try:
        await transport.connect()
        logger.info(f"Tailing log from {port} for {duration_s}s...")
        
        start = datetime.now(timezone.utc)
        async def tail_loop():
            while True:
                line = await transport.read_line()
                if line:
                    ts = datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]
                    print(f"[{ts}] {line}")
                
                elapsed = (datetime.now(timezone.utc) - start).total_seconds()
                if elapsed >= duration_s:
                    break
        
        await tail_loop()
        
    finally:
        await transport.disconnect()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Arduino Log Reader")
    parser.add_argument("--port", default="COM15", help="Serial port")
    parser.add_argument("--baudrate", type=int, default=921600, help="Baud rate")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--tail", type=int, default=0, help="Tail live log for N seconds")
    args = parser.parse_args()
    
    if args.tail > 0:
        asyncio.run(tail_live_log(args.port, args.baudrate, args.tail))
    else:
        log = asyncio.run(read_boot_log(args.port, args.baudrate, Path(args.output) if args.output else None))
        print(log)
