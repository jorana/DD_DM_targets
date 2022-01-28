import dddm
from unittest import skipIf
from unittest import TestCase
import dddm
import numpy as np

@skipIf(not dddm.utils.is_installed('pymultinest'), 'pymultinest is not installed')
@skipIf(dddm.utils.is_windows(), "Multinest only works on linux")
class NestleTest(TestCase):
    def setUp(self) -> None:
        self.ct = dddm.test_context()

    def test_multinest_shielded_full_astrophysics(self,):
        self.test_multinest(halo_name='shielded_shm', fit_parameters=dddm.statistics.get_param_list())

    def test_multinest_shielded(self,):
        self.test_multinest(halo_name='shielded_shm')

    def test_multinest(self, halo_name='shm', fit_parameters=('log_mass', 'log_cross_section',)):
        mw = 50
        cross_section = 1e-45
        sampler = self.ct.get_sampler_for_detector(
            wimp_mass=mw,
            cross_section=cross_section,
            sampler_name='multinest',
            detector_name='Xe_simple',
            prior="Pato_2010",
            halo_name=halo_name,
            detector_kwargs=None,
            halo_kwargs=None if halo_name == 'shm' else dict(location='XENON'),
            sampler_kwargs=dict(nlive=100, tol=0.1, verbose=0),
            fit_parameters=fit_parameters,
        )
        sampler.run()
        results = sampler.get_summary()

        for i, (thing, expected, avg) in enumerate(
                zip(
                    fit_parameters,
                    [getattr(sampler, f) for f in fit_parameters],
                    results['best_fit']
                )):
            std = np.sqrt(results['cov_matrix'][i][i])
            nsigma_off = np.abs(expected - avg) / std
            message = f'For {thing}: expected {expected:.2f} yielded different results {avg:.2f} +/- {std:.2f}. Off by {nsigma_off:.1f} sigma'
            self.assertTrue(nsigma_off < 4, message)
