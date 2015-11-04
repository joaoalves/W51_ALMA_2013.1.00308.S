"""
http://docs.astropy.org/en/stable/io/fits/appendix/faq.html#how-can-i-create-a-very-large-fits-file-from-scratch
"""
from astropy import log
from astropy.io import fits
import numpy as np
import glob
import re
import os
from astropy.utils.console import ProgressBar

nchans_total = {ii: 3840 for ii in range(8)}

def make_spw_cube(spw='spw{0}', spwnum=0, fntemplate='w51pointing32'):
    spw = spw.format(spwnum)

    # First set up an empty file
    if not os.path.exists('{1}_{0}_lines.fits'.format(spw, fntemplate)):
        header_fn = glob.glob('piece_of_{1}_cube.{0}.channels0to*.image.fits'.format(spw, fntemplate))
        if len(header_fn) != 1:
            raise ValueError("Found too many or too few matches: {0}".format(header_fn))
        header = fits.getheader(header_fn[0])
        # Make an arbitrary, small data before prepping the header
        data = np.zeros((100, 100), dtype=np.float32)
        hdu = fits.PrimaryHDU(data=data, header=header)
        # Set the appropriate output size (this can be extracted from the LISTOBS)
        header['NAXIS3'] = nchans_total[spwnum]
        # Write to disk
        header.tofile('{1}_{0}_lines.fits'.format(spw, fntemplate))
        # Using the 'append' io method, update the *header*
        with open('{1}_{0}_lines.fits'.format(spw, fntemplate), 'rb+') as fobj:
             # Seek past the length of the header, plus the length of the
             # data we want to write.
             # The -1 is to account for the final byte that we are about to
             # write:
             # 'seek' works on bytes, so divide #bits / (bytes/bit)
             fobj.seek(len(header.tostring()) + (header['NAXIS1'] *
                                                 header['NAXIS2'] *
                                                 header['NAXIS3'] *
                                                 np.abs(header['BITPIX'])/8) -
                       1)
             fobj.write('\0')

    # Find the appropriate files (this is NOT a good way to do this!  Better to
    # provide a list.  But wildcards are quick & easy...
    files = glob.glob("piece_of_{1}_cube.{0}.chan*fits".format(spw,fntemplate))
    log.info(str(files))

    # Extract the appropriate pixel indices from the file name.
    # A more sophisticated approach is probably better, in which the individual
    # cubes are inspected for their start/end frequencies.
    # But, on the other hand, for this process to make any sense at all, you
    # have to have done the original cube imaging right
    def getinds(fn):
        inds = re.search('channels([0-9]*)to([0-9]*)', fn).groups()
        return [int(ii) for ii in inds]

    # open the file in update mode (it should have the right dims now)
    hdul = fits.open('{1}_{0}_lines.fits'.format(spw, fntemplate), mode='update')
    for fn in ProgressBar(files):
        log.info("{0} {1}".format(getinds(fn), fn))
        ind0,ind1 = getinds(fn)
        plane = hdul[0].data[ind0]
        if np.all(plane == 0):
            log.info("Replacing indices {0} {1}".format(getinds(fn), fn))
            hdul[0].data[ind0:ind1,:,:] = fits.getdata(fn)
            hdul.flush()