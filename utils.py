"""
"""


import sys


def hdms_to_dd(hdms: str) -> float:
    """Converts degrees minutes seconds to decimal degrees.

    Input is assumed to have a hemisphere indicator, one of {E, W, N, S}.
    Numeric parts are assumed to be space separated.
    Overall input format like 'W30 24 15'.
    Output is positive for Northern and Eastern hemispheres,
    and negative for Western and Southern hemispheres.
    """
    hemisphere = hdms.strip()[0]
    deg, mins, secs =  [int(s) for s in hdms.strip()[1:].split(' ')]
    if hemisphere in ['E', 'N']:
        sign = 1.0
    elif hemisphere in ['W', 'S']:
        sign = -1.0
    else:
        sys.exit('Location string must be formatted like "W30 24 15", with hemisphere indicated by one of {W, E, N, S}.')
    return sign*(deg + (mins/60.0) + (secs/3600.0))