import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple, cast

import typer
from praatio import textgrid

Interval = Tuple[float, float, str]


def _read_textgrid(path: Path) -> Dict[str, List[Interval]]:
    grid = textgrid.openTextgrid(str(path), includeEmptyIntervals=True)
    intervals_by_tier: Dict[str, List[Interval]] = {}

    for tier_name in grid.tierNames:
        entries: List[Interval] = []
        for entry in grid.getTier(tier_name).entries:
            if len(entry) == 3:
                start, end, label = cast(Tuple[float, float, str], entry)
            else:
                point, label = cast(Tuple[float, str], entry)
                start = end = point
            entries.append((start, end, label))
        intervals_by_tier[tier_name] = entries

    return intervals_by_tier


def _selected_tiers(
    available: List[str], requested: Optional[List[str]]
) -> List[str]:
    selected = requested or available
    unknown = [name for name in selected if name not in available]
    if unknown:
        raise typer.BadParameter(
            f"Tier(s) not found: {', '.join(unknown)}. "
            f"Available tiers: {', '.join(available)}"
        )
    return selected


def _output_paths(
    output_path: Path, tier_names: List[str], separate: bool
) -> Dict[str, Path]:
    if separate:
        return {
            name: output_path.with_name(
                f"{output_path.stem}_{name}{output_path.suffix}"
            )
            for name in tier_names
        }
    return {"combined": output_path}


def _write_intervals_csv(
    output_path: Path,
    intervals_by_tier: Dict[str, List[Interval]],
    tier_names: List[str],
) -> int:
    rows = 0
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(("tier", "start", "end", "label"))
        for tier_name in tier_names:
            for start, end, label in intervals_by_tier[tier_name]:
                writer.writerow((tier_name, start, end, label))
                rows += 1
    return rows


def _write_sampled_csv(
    output_path: Path,
    intervals_by_tier: Dict[str, List[Interval]],
    tier_names: List[str],
    frequency: float,
    total_time: float,
    include_instances: bool = False,
) -> int:
    row_count = int(total_time * frequency)
    if row_count == 0 and total_time > 0:
        row_count = 1

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        columns = ["time"]
        for tier_name in tier_names:
            columns.extend((tier_name, f"{tier_name}_int"))
            if include_instances:
                columns.append(f"{tier_name}_instance")
        writer.writerow(columns)

        instance_numbers_by_tier: Dict[str, List[Optional[int]]] = {}
        for tier_name in tier_names:
            next_instance_by_label: Dict[str, int] = {}
            instance_numbers: List[Optional[int]] = []
            for _, _, label in intervals_by_tier[tier_name]:
                if label:
                    instance = next_instance_by_label.get(label, 0)
                    next_instance_by_label[label] = instance + 1
                    instance_numbers.append(instance)
                else:
                    instance_numbers.append(None)
            instance_numbers_by_tier[tier_name] = instance_numbers

        for sample_number in range(row_count):
            timestamp = sample_number / frequency
            labels = []
            for tier_name in tier_names:
                label = ""
                interval_number = ""
                instance_number = ""
                for interval_index, (start, end, interval_label) in enumerate(
                    intervals_by_tier[tier_name]
                ):
                    if start <= timestamp < end:
                        label = interval_label
                        interval_number = interval_index
                        if include_instances:
                            instance = instance_numbers_by_tier[tier_name][
                                interval_index
                            ]
                            if instance is not None:
                                instance_number = instance
                        break
                labels.extend((label, interval_number))
                if include_instances:
                    labels.append(instance_number)
            writer.writerow((timestamp, *labels))
    return row_count


def convert_command(
    frequency: float,
    textgrid_file: str,
    output_csv: str,
    tier_names: Optional[List[str]] = typer.Option(
        None,
        "--tier",
        help="Tier to convert. Repeat this option to select multiple tiers.",
    ),
    separate: bool = typer.Option(
        False,
        "--separate",
        help="Write each selected tier to its own CSV file.",
    ),
    intervals_output: bool = typer.Option(
        False,
        "--intervals",
        "--legacy",
        help="Write the tier,start,end,label format instead.",
    ),
    include_instances: bool = typer.Option(
        False,
        "--instances",
        "--include-instances",
        help="Add per-label occurrence numbers for each selected tier.",
    ),
) -> None:
    """Convert a TextGrid into sampled or interval-row CSV files."""
    textgrid_path = Path(textgrid_file)
    output_path = Path(output_csv)
    if not textgrid_path.exists():
        raise typer.BadParameter(
            f"TextGrid file does not exist: {textgrid_path}"
        )

    intervals_by_tier = _read_textgrid(textgrid_path)
    selected = _selected_tiers(list(intervals_by_tier), tier_names)
    paths = _output_paths(output_path, selected, separate)

    total_time = max(
        (end for values in intervals_by_tier.values() for _, end, _ in values),
        default=0.0,
    )

    if intervals_output:
        print(f"Read TextGrid: {textgrid_path}")
        print("Output mode: interval rows")
        print(f"Tiers: {', '.join(selected)}")
        print(f"Tier count: {len(selected)}")
        for name, path in paths.items():
            rows = _write_intervals_csv(path, intervals_by_tier, [name] if separate else selected)
            print(f"Wrote: {path} ({rows} rows)")
        return

    if frequency <= 0:
        raise typer.BadParameter(
            "Frequency must be greater than zero unless --intervals is used."
        )

    print("\n=== TEXTGRID CONVERSION ===")
    print(f"Read TextGrid: {textgrid_path}")
    print(f"Output mode: {'separate files' if separate else 'combined file'}")
    print(f"Tiers: {', '.join(selected)}")
    print(f"Tier count: {len(selected)}")
    print(f"Frequency: {frequency:g} Hz")
    columns_per_tier = 3 if include_instances else 2
    print(f"Columns: {1 + len(selected) * columns_per_tier}")
    print(f"Total time: {total_time:g} seconds")
    for name, path in paths.items():
        rows = _write_sampled_csv(
            path,
            intervals_by_tier,
            [name] if separate else selected,
            frequency,
            total_time,
            include_instances,
        )
        print(f"Wrote: {path}")
        print(f"Rows: {rows}")
    print("=== COMPLETE ===")
