# Written with svn r14 in mind, where files are now explicitly set to save in
# binary output

from datetime import datetime
from matplotlib import pyplot as plt
import numpy as np
from typing import Tuple, Callable
from pathlib import Path
import scipy as sp
from VHF.user_io import get_files, user_input_bool
from VHF.parse import VHFparser


def get_phase(o: VHFparser) -> np.ndarray:
    """Return phi/2pi; phi:= atan(Q/I).

    Input
    -----
    o: VHFparser class, initialised with file being parsed.

    Returns
    -----
    phase: Divided by 2pi
    """
    if o.reduced_phase is None:
        phase = -np.arctan2(o.i_arr, o.q_arr)
        phase /= 2 * np.pi
        phase -= o.m_arr
        o.reduced_phase = phase
    return o.reduced_phase


def get_radius(o: VHFparser) -> np.ndarray:
    """Return norm of (I, Q)."""
    result = np.hypot(o.i_arr, o.q_arr)
    lower_lim = int(1e5)
    print(
        f"Radius Mean: {np.mean(result[lower_lim:])}\nRadius Std Dev: {np.std(result[lower_lim:])}"
    )
    return result


def get_spec(o: VHFparser) -> Tuple[np.ndarray, np.ndarray]:
    """(f, Pxx_den) from x(t) signal, by periodogram method."""
    p = o.reduced_phase
    # f, spec = sp.signal.welch(2*np.pi*p, fs=o.header['sampling freq'])
    f, spec = sp.signal.periodogram(
        2 * np.pi * p, fs=o.header["sampling freq"])
    return f, spec


def plot_rad_spec(radius: bool, velocity: bool, spectrum: bool) -> Callable:
    """Yield desired function for plotting phase, radius and spectrum.

    Input
    -----
    radius: bool
        Plots sqrt(I^2+Q^2)
    velocity: bool
        Plots r[i+1] - r[i] for all valid i, divided by time between samples.
    spectrum: bool
        Plots periodogram
    """

    # consistent plot methods across functions returned
    def scatter_hist(y, ax_histy):
        binwidth = (np.max(y) - np.min(y)) / 100
        bins = np.arange(np.min(y) - binwidth, np.max(y) + binwidth, binwidth)
        ax_histy.hist(y, bins=bins, orientation="horizontal")

    def plotphi(ax, o: VHFparser, phase: np.ndarray):
        t = np.arange(len(phase)) / o.header["sampling freq"]
        ax.plot(t, phase, color="mediumblue", linewidth=0.2, label="Phase")
        # ax.plot(-parsed.m_arr, color='red', linewidth=0.2, label='Manifold')
        ax.set_ylabel(r"$\phi_d$/2$\pi$rad", usetex=True)
        ax.set_xlabel(r"$t$/s", usetex=True)

    def plotr(r_ax, o: VHFparser, phase: np.ndarray):
        t = np.arange(len(phase)) / o.header["sampling freq"]
        lower_lim = np.max(np.where(t < 0.003))
        r_ax.plot(
            t[lower_lim:],
            rs := get_radius(o)[lower_lim:],
            color="mediumblue",
            linewidth=0.2,
            label="Radius",
        )
        r_ax.set_ylabel(r"$r$/ADC units", usetex=True)
        r_ax.set_xlabel(r"$t$/s", usetex=True)
        r_ax_histy = r_ax.inset_axes([1.01, 0, 0.08, 1], sharey=r_ax)
        r_ax_histy.tick_params(axis="y", labelleft=False, length=0)
        scatter_hist(rs, r_ax_histy)

    def plotsp(sp_ax, o: VHFparser, *_):
        sp_ax.scatter(
            *get_spec(o),
            color="mediumblue",
            linewidth=0.2,
            label="Spectrum Density",
            s=0.4,
        )
        sp_ax.set_ylabel(
            "Phase 'Spec' Density /rad$^2$Hz$^-$$^1$", usetex=True)
        sp_ax.set_xlabel("$f$ [Hz]", usetex=True)
        sp_ax.set_yscale("log")
        sp_ax.set_xscale("log")

    def plotv(v_ax, o: VHFparser, phase: np.ndarray):
        t = np.arange(len(phase)-1) / o.header["sampling freq"]
        velocity = np.diff(phase) * o.header["sampling freq"]
        lower_lim = np.max(np.where(t < 0.003))
        v_ax.plot(
            t[lower_lim:],
            velocity[lower_lim:],
            color="mediumblue",
            linewidth=0.2,
            label="Phase First Derivative",
        )
        v_ax.set_ylabel(r"$r'$/ADC units $s^{-1}$", usetex=True)
        v_ax.set_xlabel(r"$t$/s", usetex=True)

    def plot_generic(o: VHFparser, phase: np.ndarray):
        options = [radius, velocity, spectrum]
        options_plots = [plotr, plotv, plotsp]
        options_sharex = [True, True, False]  # sharex with axs[0], i.e.: r
        n = 1+sum(options)
        fig, axs = plt.subplots(nrows=n, ncols=1)
        i = 0
        plotphi(axs[i], o, phase)
        for option, plot_, opt_x in zip(options, options_plots, options_sharex):
            if option:
                i += 1
                ax = axs[i]
                if opt_x:
                    ax.sharex(axs[0])
                plot_(ax, o, phase)

        return fig

    return plot_generic


def main():
    print("Please select files intended for plotting.")
    files = get_files(init_dir=str(Path(__file__).parent))

    print(f"{files = }")
    if files is None:
        print("No files!")
        return

    if isinstance(files, list):
        file: Path = files[0]
        print("This script has not implemented plotting and saving all files.")
    elif isinstance(files, map):
        file: Path = next(files)
        print("This script has not implemented plotting and saving all files.")
    else:
        file: Path = files

    parsed = VHFparser(file)
    print(f"Debug {parsed.header = }")
    plot_radius = user_input_bool("Do you want to plot the radius?")
    plot_velocity = user_input_bool("Do you want to plot the radius first derivative?")
    plot_spec = user_input_bool("Do you want to plot the spectrum?")

    phase = get_phase(parsed)
    fig = plot_rad_spec(plot_radius, plot_velocity, plot_spec)(parsed, phase)

    view_const = 2.3
    fig.legend()
    fig.set_size_inches(view_const * 0.85 *
                        (8.25 - 0.875 * 2), view_const * 2.5)
    fig.tight_layout()
    fig.canvas.manager.set_window_title(str(file))
    plt.show(block=True)


if __name__ == "__main__":
    main()
