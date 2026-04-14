"""Supporting calculation methods.

Functions
---------
hdms_to_dd
switch_lon_lims

"""


def hdms_to_dd(hdms: str) -> float:
    """Converts degrees minutes seconds to decimal degrees.

    Input is assumed to have a hemisphere indicator, one of {E, W, N, S}.
    Numeric parts are assumed to be space separated.
    Overall input format like 'W30 24 15'.
    Output is positive for Northern and Eastern hemispheres,
    and negative for Western and Southern hemispheres.

    Parameters
    ----------
    hdms
        String containing a single coordinate constituent
        (latitude or longitude) in degrees, minutes, and seconds.

    Returns
    -------
    Float
        The input converted to decimal degrees. 
        
    """
    hemisphere = hdms.strip()[0]
    deg, mins, secs =  [int(s) for s in hdms.strip()[1:].split(' ')]
    if hemisphere in ['E', 'N']:
        sign = 1.0
    elif hemisphere in ['W', 'S']:
        sign = -1.0
    else:
        raise ValueError('Location string must be formatted like "W30 24 15", with hemisphere indicated by one of {W, E, N, S}.')
    return sign*(deg + (mins/60.0) + (secs/3600.0))


def switch_lon_lims(lon_list, min_lon=0.0):
    """Converts longitude values to a specified range.
    
    Parameters    
    ----------
    lon_list
        A list or array of longitude values.
    min_lon
        The minimum longitude value for the output range. 
        Default is 0.0, which gives a range of [0, 360). 
        Setting min_lon to -180.0 gives a range of [-180, 180).
    Returns
    -------
    Longitude values converted to the specified range, with 
    the same type as 'lon_list'.
    """
    result = (lon_list - min_lon) % 360.0 + min_lon
    return result