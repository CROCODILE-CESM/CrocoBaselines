# ...existing code...
from regional_mom6 import *
import argparse
from pathlib import Path
from typing import List
import xarray as xr
import subprocess
import shutil
import pandas as pd

def generate_expts() -> List:
    """Generate a list of experiment configurations for baseline grids."""
    # Northern Hemisphere Basic
    north_hem_basic = experiment.create_empty()
    north_hem_basic.hgrid_type == "even_spacing"
    north_hem_basic.resolution = 0.05
    north_hem_basic.mom_input_dir = Path("north_hem_basic_input")
    north_hem_basic.mom_input_dir.mkdir(exist_ok=True)
    north_hem_basic.latitude_extent = [38, 41]
    north_hem_basic.longitude_extent = [304, 307]
    north_hem_basic.date_range = tuple(pd.date_range("2020-01-01", "2020-01-05"))
    north_hem_basic.number_vertical_layers = 10
    north_hem_basic.layer_thickness_ratio = 10
    north_hem_basic.depth = 2000
    north_hem_basic.expt_name = "north_hem_basic"
    # South Long Seam
    south_long_seam = experiment.create_empty()
    south_long_seam.hgrid_type == "even_spacing"
    south_long_seam.resolution = 0.05
    south_long_seam.mom_input_dir = Path("south_long_seam_input")
    south_long_seam.mom_input_dir.mkdir(exist_ok=True)
    south_long_seam.latitude_extent = [-25, -23]
    south_long_seam.longitude_extent = [175, 181]
    south_long_seam.date_range = tuple(pd.date_range("2020-01-01", "2020-01-05"))
    south_long_seam.number_vertical_layers = 10
    south_long_seam.layer_thickness_ratio = 10
    south_long_seam.depth = 2000
    south_long_seam.expt_name = "south_long_seam"

    # South Prime Seam
    south_prime_seam = experiment.create_empty()
    south_prime_seam.hgrid_type == "even_spacing"
    south_prime_seam.resolution = 0.05
    south_prime_seam.mom_input_dir = Path("south_prime_seam_input")
    south_prime_seam.mom_input_dir.mkdir(exist_ok=True)
    south_prime_seam.latitude_extent = [-18, -16]
    south_prime_seam.longitude_extent = [-3, 1]
    south_prime_seam.date_range = tuple(pd.date_range("2020-01-01", "2020-01-05"))
    south_prime_seam.number_vertical_layers = 10
    south_prime_seam.layer_thickness_ratio = 10
    south_prime_seam.depth = 2000
    south_prime_seam.expt_name = "south_prime_seam"

    return [north_hem_basic, south_long_seam, south_prime_seam]


def generate_grids(expts) -> List:

    grids = []
    for expt in expts:
        expt.hgrid = expt._make_hgrid()
        grids.append(expt.hgrid)

    return grids
def generate_vgrids(expts)-> List:
    grids = []
    for expt in expts:
        expt.vgrid = expt._make_vgrid()
        grids.append(expt.vgrid)

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

def generate_raw_data(expts):
    for expt in expts:
        if not (expt.mom_input_dir/"ic_unprocessed.nc").exists():
            print("Can't find raw data, so downloading it")
            expt.get_glorys(
                raw_boundaries_path=expt.mom_input_dir
            )
            script_path = Path(expt.mom_input_dir) / "get_glorys_data.sh"
            script_path.chmod(script_path.stat().st_mode | 0o111)  # adds execute permission
            result = subprocess.run(
                [str(script_path)],  # directly execute
                capture_output=True, # optional
                text=True
            )
            print(result.stdout)


def generate_forcings(expts):
    # Define a mapping from the GLORYS variables and dimensions to the MOM6 ones
    generate_raw_data(expts)
    ocean_varnames = {"time": "time",
                    "yh": "latitude",
                    "xh": "longitude",
                    "zl": "depth",
                    "eta": "zos",
                    "u": "uo",
                    "v": "vo",
                    "tracers": {"salt": "so", "temp": "thetao"}
                    }
    for expt in expts:

        # Set up the initial condition
        expt.setup_initial_condition(
            expt.mom_input_dir / "ic_unprocessed.nc", # directory where the unprocessed initial condition is stored, as defined earlier
            ocean_varnames,
            arakawa_grid="A"
            )

        # Set up the four boundary conditions. Remember that in the glorys_path, we have four boundary files names north_unprocessed.nc etc.
        expt.setup_ocean_state_boundaries(
                expt.mom_input_dir,
                ocean_varnames,
                arakawa_grid = "A",
                bathymetry_path = expt.bathymetry_path
                )

def save_grids_to_baseline(expts: List, outdir: Path, prefix: str = ""):
    """Save generated grids to the specified baseline directory."""
    outdir.mkdir(parents=True, exist_ok=True)
    if not expts:
        print("No grids to save (generate_grids returned empty list).")
        return
    for i, expt in enumerate(expts):
        name = ("grid_"+getattr(expt, "expt_name", None)) or f"grid_{i}"
        filename = f"{prefix + '_' if prefix else ''}{name}.nc"
        outpath = outdir / filename
        print(f"Writing grid '{name}' -> {outpath}")
        expt.hgrid.to_netcdf(outpath)

def save_vgrids_to_baseline(expts: List, outdir: Path, prefix: str = ""):
    """Save generated grids to the specified baseline directory."""
    outdir.mkdir(parents=True, exist_ok=True)
    if not expts:
        print("No grids to save (generate_grids returned empty list).")
        return
    for i, expt in enumerate(expts):
        name = ("vgrid_"+getattr(expt, "expt_name", None)) or f"vgrid_{i}"
        filename = f"{prefix + '_' if prefix else ''}{name}.nc"
        outpath = outdir / filename
        print(f"Writing vgrid '{name}' -> {outpath}")
        expt.vgrid.to_netcdf(outpath)


def save_bathys_to_baseline(expts: List, outdir: Path, prefix: str = ""):
    outdir.mkdir(parents=True, exist_ok=True)
    for i, expt in enumerate(expts):
        name = f"bathy_{expt.expt_name}"
        filename = f"{prefix + '_' if prefix else ''}{name}.nc"
        outpath = outdir / filename
        print(f"Writing bathymetry '{name}' -> {outpath}")
        expt.bathymetry.to_netcdf(outpath)  # assuming Topo implements `write()`
def save_forcings_to_baseline(expts: List, outdir: Path, prefix: str = ""):
    outdir.mkdir(parents=True, exist_ok=True)
    for i, expt in enumerate(expts):
        # Copy files that end with _ic or start with forcing_ to the outdir from expt.mom_input_dir
        # Iterate and copy
        for file in expt.mom_input_dir.iterdir():
            if file.is_file() and (file.name.endswith("_ic") or file.name.startswith("forcing_")):
                dest = Path(outdir) / f"{expt.expt_name}_{file.name}"
                shutil.copy2(file, dest)  # copy2 preserves metadata
                print(f"Copied: {file.name} to {dest.name}")

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
    p.add_argument(
        "--with-forcings",
        action="store_true",
        help="If set, generate and save forcing files for each grid.",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    outdir = Path(args.baseline_dir)
    expts = generate_expts()
    grids = generate_grids(expts)  # replace with real implementation
    vgrids = generate_vgrids(expts)
    save_grids_to_baseline(expts, outdir, prefix=args.prefix)
    save_vgrids_to_baseline(expts, outdir, prefix=args.prefix)

    if args.with_bathy:
        print("\n-- Generating bathymetry because --with-bathy was specified --")
        topos = generate_bathys(expts)
        save_bathys_to_baseline(topos, outdir, prefix=args.prefix)
    else:
        print("\n-- Skipping bathymetry generation (use --with-bathy to enable) --")

    if args.with_forcings:
        print("\n-- Generating forcings because --with-forcings was specified --")
        names = []

        generate_forcings(expts)
        save_forcings_to_baseline(expts, outdir, prefix=args.prefix)
# ...existing code...
