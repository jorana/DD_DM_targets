"""Introduce detector effects into the expected detection spectrum"""
import warnings
import numba
import numpy as np
import dddm
from .spectrum import GenSpectrum
import typing as ty

export, __all__ = dddm.exporter()


@export
class DetectorSpectrum(GenSpectrum):
    """
    Convolve a recoil spectrum with the detector effects:
     - background levels
     - energy resolution
     - energy threshold
    """

    def __str__(self):
        return f'Detector effects convolved {super().__repr__()}'

    def _calculate_counts(self,
                          wimp_mass: ty.Union[int, float],
                          cross_section: ty.Union[int, float],
                          poisson: bool,
                          bin_centers: np.ndarray,
                          bin_width: np.ndarray,
                          bin_edges: np.ndarray,
                          ) -> np.ndarray:
        """

        :return: spectrum taking into account the detector properties
        """
        # get the spectrum
        rates = self.spectrum_simple(bin_centers,
                                     wimp_mass=wimp_mass,
                                     cross_section=cross_section)

        # pay close attention, the events in the bg_func are already taking into
        # account the det. efficiency et cetera. Hence the number here should be
        # multiplied by the total exposure (rather than the effective exposure that
        # is multiplied by at the end of this subroutine. Hence the bg rates obtained
        # from that function is multiplied by the ratio between the two.
        rates += self.background_function(bin_centers) * (self.exposure_tonne_year /
                                                          self.effective_exposure)

        # Smear the rates with the detector resolution
        sigma = self.resolution(bin_centers)
        rates = np.array(smear_signal(rates, bin_centers, sigma, bin_width))

        # Set the rate to zero for energies smaller than the threshold
        rates = self.above_threshold(rates, bin_edges, self.energy_threshold_kev)

        # Calculate the total number of events per bin
        rates = rates * bin_width * self.effective_exposure
        return rates

    @staticmethod
    @numba.njit
    def above_threshold(rates: np.ndarray, e_bin_edges: np.ndarray, e_thr: ty.Union[float, int]):
        """
        Apply threshold to the rates. We are right edge inclusive
        bin edges : |bin0|bin1|bin2|
        e_thr     :        |
        bin0 -> 0
        bin1 -> fraction of bin1 > e_thr
        bin2 -> full content

        :param rates: bins with the number of counts
        :param e_bin_edges: 2d array of the left, right bins
        :param e_thr: energy threshold
        :return: rates with energy threshold applied
        """
        for r_i, r in enumerate(rates):
            left_edge, right_edge = e_bin_edges[r_i]
            if left_edge >= e_thr:
                # From now on all the bins will be above threshold we don't
                # have to set to 0 anymore
                break
            if right_edge <= e_thr:
                # this bin is fully below threshold
                rates[r_i] = 0
                continue
            elif left_edge <= e_thr and e_thr <= right_edge:
                fraction_above = (right_edge - e_thr) / (right_edge - left_edge)
                rates[r_i] = r * fraction_above
            else:
                print(left_edge, right_edge, e_thr)
                raise ValueError('How did this happen?')

        return rates


def smear_signal(rate: np.ndarray,
                 energy: np.ndarray,
                 sigma: np.ndarray,
                 bin_width: np.ndarray
                 ):
    """

    :param rate: counts/bin
    :param energy: energy bin_center
    :param sigma: energy resolution
    :param bin_width: should be scalar of the bin width
    :return: the rate smeared with the specified energy resolution at given
    energy

    This function takes a binned DM-spectrum and takes into account the energy
    resolution of the detector. The rate, energy and resolution should be arrays
    of equal length. The the bin_width
    """
    if np.any(sigma < bin_width):
        warnings.warn(f'Resolution {np.mean(sigma)} smaller than bin_width {bin_width}!',
                      UserWarning)
        return rate
    result_buffer = np.zeros(len(rate), dtype=np.float64)
    return _smear_signal(rate, energy, sigma, bin_width, result_buffer)


@numba.njit
def _smear_signal(rate, energy, sigma, bin_width, result_buffer):
    # pylint: disable=consider-using-enumerate
    for i in range(len(energy)):
        res = 0.
        # pylint: disable=consider-using-enumerate
        for j in range(len(rate)):
            # see formula (5) in https://arxiv.org/abs/1012.3458
            res = res + (bin_width[j] * rate[j] *
                         (1. / (np.sqrt(2. * np.pi) * sigma[j])) *
                         np.exp(-(((energy[i] - energy[j]) ** 2.) / (2. * sigma[j] ** 2.)))
                         )
            # TODO
            #  # at the end of the spectrum the bg-rate drops as the convolution does
            #  # not take into account the higher energies.
            #  weight = length / (j-length)
            #  res = res * weight
        result_buffer[i] = res
    return result_buffer


def _epsilon(e_nr, atomic_number_z):
    return 11.5 * e_nr * (atomic_number_z ** (-7 / 3))


def _g(e_nr, atomic_number_z):
    eps = _epsilon(e_nr, atomic_number_z)
    a = 3 * (eps ** 0.15)
    b = 0.7 * (eps ** 0.6)
    return a + b + eps


@export
def lindhard_quenching_factor(e_nr, k, atomic_number_z):
    """
    https://arxiv.org/pdf/1608.05381.pdf
    """
    g = _g(e_nr, atomic_number_z)
    a = k * g
    b = 1 + k * g
    lindhard_factor = a / b
    return lindhard_factor


@export
def lindhard_quenching_factor_xe(e_nr):
    """
    Xenon Lindhard nuclear quenching factor

    """
    return lindhard_quenching_factor(e_nr=e_nr, k=0.1735, atomic_number_z=54)


@export
def lindhard_quenching_factor_ge(e_nr):
    return lindhard_quenching_factor(e_nr=e_nr, k=0.162, atomic_number_z=32)


@export
def lindhard_quenching_factor_si(e_nr):
    return lindhard_quenching_factor(e_nr=e_nr, k=0.161, atomic_number_z=14)
