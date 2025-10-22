# ...existing code...
from mom6_bathy.grid import *
try:
    from CrocoDash.topo import *
except:
    from mom6_bathy.topo import *
import argparse
from pathlib import Path
from typing import List


def generate_grids() -> List:
    """
    Placeholder: build and return a list of grid objects.
    Replace this with your actual grid-generation logic.
    Each grid object should implement `write_supergrid(path)` and preferably have a `name` attribute.
    """

    # Northern Hemisphere Basic
    grid_north_hem_basic = Grid(
        resolution=0.05,  # in degrees
        xstart=304,  # min longitude in [0, 360]
        lenx=3.0,  # longitude extent in degrees
        ystart=38.0,  # min latitude in [-90, 90]
        leny=3.0,  # latitude extent in degrees
        name="north_hem_basic",
    )
    # South Long Seam
    grid_south_long_seam = Grid(
        resolution=0.05,  # in degrees
        xstart=175.0,  # min longitude in [0, 360]
        lenx=6.0,  # longitude extent in degrees
        ystart=-25.0,  # min latitude in [-90, 90]
        leny=2.0,  # latitude extent in degrees
        name="south_long_seam",
    )

    # South Prime Seam
    grid_south_prime_seam = Grid(
        resolution=0.05,  # in degrees
        xstart=357,  # min longitude in [0, 360]
        lenx=4.0,  # longitude extent in degrees
        ystart=-18.0,  # min latitude in [-90, 90]
        leny=2.0,  # latitude extent in degrees
        name="south_prime_seam",
    )

    return [grid_north_hem_basic, grid_south_long_seam, grid_south_prime_seam]

def generate_bathys(grids) -> List:
    """
    
    """
    bathymetry_path = Path("/glade/campaign/cgd/oce/projects/CROCODILE/workshops/2025/CrocoDash/data/gebco/GEBCO_2024.nc")

    topos = []
    for grid in grids:
        topo = Topo(
            grid = grid,
            min_depth = 9.5, # in meters
        )
        print(f"Generating bathymetry for grid: {grid.name}")

        try:
            topo.set_from_dataset(
                bathymetry_path = bathymetry_path,
                longitude_coordinate_name="lon",
                latitude_coordinate_name="lat",
                vertical_coordinate_name="elevation",
                write_to_file = False
            )
        except:
            topo.interpolate_from_file(
            file_path = bathymetry_path,
            longitude_coordinate_name="lon",
            latitude_coordinate_name="lat",
            vertical_coordinate_name="elevation"
        )
        topos.append(topo)
    return topos


def save_grids_to_baseline(grids: List, outdir: Path, prefix: str = ""):
    outdir.mkdir(parents=True, exist_ok=True)
    if not grids:
        print("No grids to save (generate_grids returned empty list).")
        return
    for i, grid in enumerate(grids):
        name = getattr(grid, "name", None) or f"grid_{i}"
        filename = f"{prefix + '_' if prefix else ''}{name}.nc"
        outpath = outdir / filename
        print(f"Writing grid '{name}' -> {outpath}")
        grid.write_supergrid(outpath)


def save_bathys_to_baseline(topos: List, outdir: Path, prefix: str = ""):
    outdir.mkdir(parents=True, exist_ok=True)
    for i, topo in enumerate(topos):
        name = getattr(topo._grid, "name", None) or f"bathy_{i}"
        filename = f"{prefix + '_' if prefix else ''}{name}_bathy.nc"
        outpath = outdir / filename
        print(f"Writing bathymetry '{name}' -> {outpath}")
        topo.write_topo(outpath)  # assuming Topo implements `write()`


def parse_args():
    p = argparse.ArgumentParser(
        description="Generate baseline supergrids and optionally bathymetry files."
    )
    p.add_argument(
        "baseline_dir",
        nargs="?",
        default="baselines",
        help="Output baselines directory",
    )
    p.add_argument(
        "--prefix", "-p", default="", help="Optional filename prefix for saved grids"
    )
    p.add_argument(
        "--with-bathy",
        action="store_true",
        help="If set, generate and save bathymetry files for each grid.",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    outdir = Path(args.baseline_dir)

    grids = generate_grids()
    save_grids_to_baseline(grids, outdir, prefix=args.prefix)

    if args.with_bathy:
        print("\n-- Generating bathymetry because --with-bathy was specified --")
        topos = generate_bathys(grids)
        save_bathys_to_baseline(topos, outdir, prefix=args.prefix)
    else:
        print("\n-- Skipping bathymetry generation (use --with-bathy to enable) --")
# ...existing code...