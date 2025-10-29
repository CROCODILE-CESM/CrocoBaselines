# ...existing code...
from regional_mom6 import *
import argparse
from pathlib import Path
from typing import List
import xarray as xr


def generate_expts() -> List:
    """Generate a list of experiment configurations for baseline grids."""
    # Northern Hemisphere Basic
    north_hem_basic = experiment.create_empty()
    north_hem_basic.hgrid_type == "even_spacing"
    north_hem_basic.resolution = 0.05
    north_hem_basic.mom_input_dir = Path("temp")
    north_hem_basic.latitude_extent = [38, 41]
    north_hem_basic.longitude_extent = [304, 307]

    # South Long Seam
    south_long_seam = experiment.create_empty()
    south_long_seam.hgrid_type == "even_spacing"
    south_long_seam.resolution = 0.05
    south_long_seam.mom_input_dir = Path("temp")
    south_long_seam.latitude_extent = [-25, -23]
    south_long_seam.longitude_extent = [175, 181]

    # South Prime Seam
    south_prime_seam = experiment.create_empty()
    south_prime_seam.hgrid_type == "even_spacing"
    south_prime_seam.resolution = 0.05
    south_prime_seam.mom_input_dir = Path("temp")
    south_prime_seam.latitude_extent = [-18, -16]
    south_prime_seam.longitude_extent = [-3, 1]

    return [north_hem_basic, south_long_seam, south_prime_seam]


def generate_grids(expts) -> List:

    grids = []
    for expt in expts:
        expt.hgrid = expt._make_hgrid()
        grids.append(expt.hgrid)

    return grids


def generate_bathys(expts) -> List:
    """
    Generate bathymetry objects for each grid.
    """
    bathymetry_path = Path(
        "/glade/campaign/cgd/oce/projects/CROCODILE/workshops/2025/CrocoDash/data/gebco/GEBCO_2024.nc"
    )

    topos = []
    for expt in expts:
        bathymetry = expt.setup_bathymetry(
            bathymetry_path=bathymetry_path,
            longitude_coordinate_name="lon",
            latitude_coordinate_name="lat",
            vertical_coordinate_name="elevation",
        )
        topos.append(bathymetry)
    return topos


def save_grids_to_baseline(grids: List, outdir: Path, prefix: str = ""):
    """Save generated grids to the specified baseline directory."""
    outdir.mkdir(parents=True, exist_ok=True)
    if not grids:
        print("No grids to save (generate_grids returned empty list).")
        return
    for i, grid in enumerate(grids):
        name = getattr(grid, "name", None) or f"grid_{i}"
        filename = f"{prefix + '_' if prefix else ''}{name}.nc"
        outpath = outdir / filename
        print(f"Writing grid '{name}' -> {outpath}")
        grid.to_netcdf(outpath)


def save_bathys_to_baseline(topos: List, outdir: Path, prefix: str = ""):
    outdir.mkdir(parents=True, exist_ok=True)
    for i, topo in enumerate(topos):
        name = f"bathy_{i}"
        filename = f"{prefix + '_' if prefix else ''}{name}.nc"
        outpath = outdir / filename
        print(f"Writing bathymetry '{name}' -> {outpath}")
        topo.to_netcdf(outpath)  # assuming Topo implements `write()`


def parse_args():
    p = argparse.ArgumentParser(
        description="Generate baseline supergrids and save to a directory."
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
    expts = generate_expts()
    grids = generate_grids(expts)  # replace with real implementation
    save_grids_to_baseline(grids, outdir, prefix=args.prefix)

    if args.with_bathy:
        print("\n-- Generating bathymetry because --with-bathy was specified --")
        topos = generate_bathys(expts)
        save_bathys_to_baseline(topos, outdir, prefix=args.prefix)
    else:
        print("\n-- Skipping bathymetry generation (use --with-bathy to enable) --")
# ...existing code...
