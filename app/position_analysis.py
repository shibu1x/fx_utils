#!/usr/bin/env python3
"""
MT5 Position Analysis - Calculate average execution prices for buy and sell positions
"""

from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class Position:
    """Represents a single trading position"""
    open_time: str
    ticket: str
    position_type: str
    size: float
    item: str
    price: float
    stop_loss: float
    take_profit: float
    market_price: float
    swap: float
    profit: float


def parse_positions_file(file_path: str) -> List[Position]:
    """
    Parse positions.txt file and extract position data

    Args:
        file_path: Path to the positions.txt file

    Returns:
        List of Position objects
    """
    positions = []

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Skip header lines (first 2 lines)
    for line in lines[2:]:
        line = line.strip()
        if not line:
            continue

        # Split by tab character
        parts = line.split('\t')
        if len(parts) < 11:
            continue

        try:
            # Remove all whitespace characters from swap and profit fields
            swap_value = parts[9].strip().replace(' ', '').replace('\u00a0', '')
            profit_value = parts[10].strip().replace(' ', '').replace('\u00a0', '')

            position = Position(
                open_time=parts[0].strip(),
                ticket=parts[1].strip(),
                position_type=parts[2].strip(),
                size=float(parts[3].strip()),
                item=parts[4].strip(),
                price=float(parts[5].strip()),
                stop_loss=float(parts[6].strip()),
                take_profit=float(parts[7].strip()),
                market_price=float(parts[8].strip()),
                swap=float(swap_value) if swap_value else 0.0,
                profit=float(profit_value) if profit_value else 0.0
            )
            positions.append(position)
        except (ValueError, IndexError) as e:
            print(f"Warning: Failed to parse line: {line[:50]}... Error: {e}")
            continue

    return positions


def calculate_average_price(positions: List[Position], position_type: str) -> Tuple[float, float, int]:
    """
    Calculate weighted average execution price for specified position type

    Args:
        positions: List of Position objects
        position_type: 'buy' or 'sell'

    Returns:
        Tuple of (average_price, total_size, count)
    """
    filtered_positions = [p for p in positions if p.position_type == position_type]

    if not filtered_positions:
        return 0.0, 0.0, 0

    total_weighted_price = sum(p.price * p.size for p in filtered_positions)
    total_size = sum(p.size for p in filtered_positions)

    average_price = total_weighted_price / total_size if total_size > 0 else 0.0

    return average_price, total_size, len(filtered_positions)


def analyze_positions_by_item(positions: List[Position], item: str) -> Dict:
    buy_avg, buy_size, buy_count = calculate_average_price(positions, 'buy')
    sell_avg, sell_size, sell_count = calculate_average_price(positions, 'sell')

    total_profit = sum(p.profit for p in positions)
    total_swap = sum(p.swap for p in positions)

    return {
        'item': item,
        'total_positions': len(positions),
        'buy': {
            'average_price': buy_avg,
            'total_size': buy_size,
            'position_count': buy_count
        },
        'sell': {
            'average_price': sell_avg,
            'total_size': sell_size,
            'position_count': sell_count
        },
        'overall': {
            'total_profit': total_profit,
            'total_swap': total_swap
        }
    }


def analyze_positions(file_path: str) -> List[Dict]:
    positions = parse_positions_file(file_path)

    items: Dict[str, List[Position]] = {}
    for p in positions:
        items.setdefault(p.item, []).append(p)

    return [analyze_positions_by_item(group, item) for item, group in sorted(items.items())]


def print_item_results(results: Dict):
    item = results['item']
    print(f"### {item}")

    print(f"- Buy:  count={results['buy']['position_count']}  size={results['buy']['total_size']:.2f}  avg={results['buy']['average_price']:.3f}")
    print(f"- Sell: count={results['sell']['position_count']}  size={results['sell']['total_size']:.2f}  avg={results['sell']['average_price']:.3f}")

    buy_avg = results['buy']['average_price']
    sell_avg = results['sell']['average_price']
    mid_price = (buy_avg + sell_avg) / 2 if buy_avg > 0 and sell_avg > 0 else 0.0
    size_diff = results['buy']['total_size'] - results['sell']['total_size']

    print(f"- Mid: {mid_price:.3f}  Spread: {abs(buy_avg - sell_avg):.3f}  Size diff: {size_diff:+.2f}")
    print(f"- Profit: {results['overall']['total_profit']:.2f}  Swap: {results['overall']['total_swap']:.2f}")


def print_analysis_results(results: List[Dict], file_name: str):
    print(f"## {file_name}\n")
    for item_results in results:
        print_item_results(item_results)
        print()


def main():
    """Main entry point"""
    data_dir = Path("/data/input/pos")

    for data_file in sorted(data_dir.glob("*.txt")):
        results = analyze_positions(str(data_file))
        file_name = data_file.stem
        print_analysis_results(results, file_name)
        print("\n")


if __name__ == "__main__":
    main()
