import time
import numpy as np
import nibabel as nb
from nipype.interfaces import nilearn as nl
from .. import images as im
from pathlib import Path

import pytest
qform_code = 1
sform_code = 1
qform = np.array([[1,   0,   0,  0],
                [0, 1,  0, 0],
                [0,  0,  1, 0],
                [0.00000000e+00,   0.00000000e+00,   0.00000000e+00, 1.00000000e+00]])
sform = np.array([[1,   0,   0, 0],
                [0,   1,  0, 0],
                [0,  0,  1, 0],
                [0.00000000e+00,   0.00000000e+00,   0.00000000e+00,1.00000000e+00]])


@pytest.mark.parametrize('qform_add, sform_add, expectation', [
            (0, 0, "no_warn"),
            (0, 1e-14, "no_warn"),
            (0, 1e-09, "no_warn"),
            (1e-6, 0, "warn"),
            (0, 1e-6, "warn"),
            (1e-5, 0, "warn"),
            (0, 1e-5, "warn"),
            (1e-3, 1e-3, "no_warn")
])
# just a diagonal of ones in qform and sform and see that this doesn't warn
# only look at the 2 areas of images.py that I added and get code coverage of those
def test_qformsform_warning(tmpdir, qform_add, sform_add, expectation):
    tmpdir.chdir()

    # make a random image
    random_data = np.random.random(size=(5, 5, 5) + (5,))
    img = nb.Nifti1Image(random_data, sform+sform_add)
    # set the qform of the image before calling it
    img.set_qform(qform+qform_add)
    img.to_filename('x.nii')
    fname ='x.nii'

    interface = im.ValidateImage()
    interface.inputs.in_file = fname
    res = interface.run()
    if expectation == 'warn':
        assert "Note on" in Path(res.outputs.out_report).read_text()
        assert len(Path(res.outputs.out_report).read_text()) > 0
    elif expectation == 'no_warn':
        assert len(Path(res.outputs.out_report).read_text()) == 0


@pytest.mark.parametrize('nvols, nmasks, ext, factor', [
    (500, 10, '.nii', 2),
    (500, 10, '.nii.gz', 5),
    (200, 3, '.nii', 1.1),
    (200, 3, '.nii.gz', 2),
    (200, 10, '.nii', 1.1),
    (200, 10, '.nii.gz', 2),
])
def test_signal_extraction_equivalence(tmpdir, nvols, nmasks, ext, factor):
    tmpdir.chdir()

    vol_shape = (64, 64, 40)

    img_fname = 'img' + ext
    masks_fname = 'masks' + ext

    random_data = np.random.random(size=vol_shape + (nvols,)) * 2000
    random_mask_data = np.random.random(size=vol_shape + (nmasks,)) < 0.2

    nb.Nifti1Image(random_data, np.eye(4)).to_filename(img_fname)
    nb.Nifti1Image(random_mask_data.astype(np.uint8), np.eye(4)).to_filename(masks_fname)

    se1 = nl.SignalExtraction(in_file=img_fname, label_files=masks_fname,
                              class_labels=['a%d' % i for i in range(nmasks)],
                              out_file='nlsignals.tsv')
    se2 = im.SignalExtraction(in_file=img_fname, label_files=masks_fname,
                              class_labels=['a%d' % i for i in range(nmasks)],
                              out_file='imsignals.tsv')

    tic = time.time()
    se1.run()
    toc = time.time()
    se2.run()
    toc2 = time.time()

    tab1 = np.loadtxt('nlsignals.tsv', skiprows=1)
    tab2 = np.loadtxt('imsignals.tsv', skiprows=1)

    assert np.allclose(tab1, tab2)

    t1 = toc - tic
    t2 = toc2 - toc

    assert t2 < t1 / factor
