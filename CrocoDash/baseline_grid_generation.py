from mom6_bathy.grid import *

try:
    from CrocoDash.topo import *
except:
    from mom6_bathy.topo import *
import argparse
from pathlib import Path
from typing import List
from CrocoDash.case import Case
from CrocoDash.vgrid import VGrid

import shutil


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

    # Global Grid - This hangs on dask for some reason
    # glofas_grid = Grid(
    #     lenx=360,
    #     leny       = 150,         # grid length in y direction
    #     cyclic_x=True   ,
    #     ystart     = -60,       # start/end 10 degrees above/below poles to avoid singularity
    #     resolution = 0.05,
    #     name = "GLOFAS",
    # )

    return [grid_north_hem_basic, grid_south_long_seam, grid_south_prime_seam]


def generate_vgrids(grids) -> list:
    vgrids = []
    for grid in grids:
        vgrids.append(
            VGrid.hyperbolic(
                nk=10,  # number of vertical levels
                depth=4000,
                ratio=20.0,  # target ratio of top to bottom layer thicknesses
            )
        )

    return vgrids


def generate_bathys(grids) -> list:
    """ """
    bathymetry_path = Path(
        "/glade/campaign/cgd/oce/projects/CROCODILE/workshops/2025/CrocoDash/data/gebco/GEBCO_2024.nc"
    )

    topos = []
    for grid in grids:
        topo = Topo(
            grid=grid,
            min_depth=9.5,  # in meters
        )
        print(f"Generating bathymetry for grid: {grid.name}")
        if grid.name == "GLOFAS":
            print("GLOFAS grid is too big, just setting spoon depth for bathy")
            topo.set_spoon(10)
        else:
            try:
                topo.set_from_dataset(
                    bathymetry_path=bathymetry_path,
                    longitude_coordinate_name="lon",
                    latitude_coordinate_name="lat",
                    vertical_coordinate_name="elevation",
                    write_to_file=False,
                )
            except:
                topo.interpolate_from_file(
                    file_path=bathymetry_path,
                    longitude_coordinate_name="lon",
                    latitude_coordinate_name="lat",
                    vertical_coordinate_name="elevation",
                )
        topos.append(topo)
    return topos


def generate_cases(topos, vgrids, names, cache_dir, cesmroot):
    cases = []
    for i, name in enumerate(names):
        inputdir = cache_dir / (name + "_input")
        caseroot = cache_dir / (name + "_case")
        case = Case(
            cesmroot=cesmroot,
            caseroot=caseroot,
            inputdir=inputdir,
            ocn_grid=topos[i]._grid,
            ocn_vgrid=vgrids[i],
            ocn_topo=topos[i],
            project="NCGD0011",
            override=False,
            machine="CESM_NOT_PORTED",
            compset="CR_JRA",
        )
        cases.append(case)
    return cases


def get_raw_data(cases: List, cache_dir: Path):
    """
    Subset and gather raw data needed for forcing generation.
    Uses cache_dir to store and reuse previously downloaded data.
    """
    cache_dir_raw_data = cache_dir / "raw_data"

    for case in cases:
        files_found = True
        case.configure_forcings(
            date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"],
            function_name="get_glorys_data_from_rda",
            too_much_data=True,
        )
        for boundary in case.boundaries:
            cache_file = cache_dir_raw_data / f"{case.ocn_grid.name}_{boundary}_raw.nc"
            if cache_file.exists():
                print(f"  Using cached raw data for {case.caseroot.name}: {cache_file}")
                # Copy into input raw directory
                shutil.copy(
                    cache_file,
                    case.inputdir / "glorys" / "large_data_workflow" / "raw_data",
                )
            else:
                files_found = False
                print(f"Cant find one {cache_file} so probably won't find any")
                break
        if not files_found:
            print(f"  Fetching raw data for {case.caseroot.name}...")
            case.configure_forcings(
                date_range=["2020-01-01 00:00:00", "2020-01-03 00:00:00"],
                function_name="get_glorys_data_from_rda",
            )


def generate_forcings(cases: List, cache_dir: Path):
    """
    Generate forcing files for each grid using raw data from cache_dir.
    """
    print("\n-- Preparing raw data for forcing generation --")
    get_raw_data(cases, cache_dir)

    forcings = []
    for case in cases:
        print(f"Generating forcing for grid: {case.name}")
        case.process_forcings()

    return


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


def save_vgrids_to_baseline(grids: List, vgrids, outdir: Path, prefix: str = ""):
    outdir.mkdir(parents=True, exist_ok=True)
    if not grids:
        print("No grids to save (generate_grids returned empty list).")
        return
    for i, grid in enumerate(grids):
        name = (getattr(grid, "name", None) or f"vgrid_{i}") + "_vgrid"
        filename = f"{prefix + '_' if prefix else ''}{name}.nc"
        outpath = outdir / filename
        print(f"Writing vgrid '{name}' -> {outpath}")
        vgrids[i].write(outpath)


def save_bathys_to_baseline(
    topos: List, outdir: Path, prefix: str = "", cache_dir=None
):
    outdir.mkdir(parents=True, exist_ok=True)
    if cache_dir is not None:
        (cache_dir / "topos").mkdir(exist_ok=True)
    for i, topo in enumerate(topos):
        name = getattr(topo._grid, "name", None) or f"bathy_{i}"
        filename = f"{prefix + '_' if prefix else ''}{name}_bathy.nc"
        outpath = outdir / filename
        print(f"Writing bathymetry '{name}' -> {outpath}")
        topo.write_topo(outpath)  # assuming Topo implements `write()`
        if cache_dir is not None:
            topo.write_topo(cache_dir / "topos" / (topo._grid.name + "_topo.nc"))


def save_forcings_to_baseline(cases: List, outdir: Path, prefix: str = ""):
    """
    Placeholder: write forcings to disk.
    Replace this with the appropriate write method for your forcing objects.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    for i, case in enumerate(cases):
        for file in (case.inputdir / "ocnice").iterdir():
            if file.is_file() and (
                file.name.startswith("forcing_") or file.name.startswith("init_")
            ):
                shutil.copy2(file, outdir / file.name)


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
    p.add_argument(
        "--with-forcings",
        action="store_true",
        help="If set, generate and save forcing files for each grid.",
    )
    return p.parse_args()


def wrap_up(cache_dir):

    ## Cache the inputdir
    """
    Searches recursively for directories ending in '_input'.
    For each one, enters 'glorys/large_data_workflow' and finds
    all files starting with 'boundary_'. Copies them into a
    'raw_data' folder next to this script, naming them:
        {parentcase}_{boundary}_raw.nc
    """

    raw_data_dir = cache_dir / "raw_data"
    topos_dir = cache_dir / "topos"
    raw_data_dir.mkdir(exist_ok=True)

    for path in cache_dir.rglob("*_input"):
        if not path.is_dir():
            continue

        case_name = path.name.removesuffix("_input")

        # Raw Data Cache
        workflow_dir = path / "glorys" / "large_data_workflow" / "raw_data"

        if not workflow_dir.is_dir():
            continue

        for file in workflow_dir.glob("*unprocessed*"):
            if file.is_file():
                boundary_name = file.name.split("_")[0]
                dest_name = f"{case_name}_{boundary_name}_raw.nc"
                dest_path = raw_data_dir / dest_name
                if not dest_path.exists():
                    shutil.copy(file, dest_path)
                    print(f"Copied {file} -> {dest_path}")

    # Delete all folders in cache_dir ending in _input or _case

    for d in cache_dir.iterdir():
        if d.is_dir() and (d.name.endswith("_input") or d.name.endswith("_case")):
            shutil.rmtree(d)
            print(f"Deleted: {d}")


if __name__ == "__main__":

    args = parse_args()
    outdir = Path(args.baseline_dir)
    cache_dir = Path(__file__).resolve().parent / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    wrap_up(cache_dir)
    grids = generate_grids()
    vgrids = generate_vgrids(grids)
    save_grids_to_baseline(grids, outdir, prefix=args.prefix)
    save_vgrids_to_baseline(grids, vgrids, outdir, prefix=args.prefix)

    if args.with_bathy:
        print("\n-- Generating bathymetry because --with-bathy was specified --")
        topos = generate_bathys(grids)
        save_bathys_to_baseline(topos, outdir, prefix=args.prefix, cache_dir=cache_dir)
    else:
        print("\n-- Skipping bathymetry generation (use --with-bathy to enable) --")
        if args.with_forcings:
            print(
                "Since bathy is skipped, and we still want forcing, we need to load previous bathy from cache"
            )
            topos_dir = cache_dir / "topos"
            topos = []
            for grid in grids:
                topos.append(
                    Topo.from_topo_file(
                        grid, topo_file_path=topos_dir / (grid.name + "_topo.nc")
                    )
                )

    if args.with_forcings:
        print("\n-- Generating forcings because --with-forcings was specified --")
        names = []

        for grid in grids:
            names.append(grid.name)
        cases = generate_cases(
            topos,
            vgrids,
            names,
            cache_dir,
            "/glade/u/home/manishrv/work/installs/CROCESM_workshop_2025",
        )
        forcings = generate_forcings(cases, cache_dir)
        save_forcings_to_baseline(forcings, outdir, prefix=args.prefix)
    else:
        print("\n-- Skipping forcing generation (use --with-forcing to enable) --")

    wrap_up(cache_dir)
