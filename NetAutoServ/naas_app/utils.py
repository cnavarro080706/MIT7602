def validate_mac_address(mac):
    """
    Validate and standardize MAC address format.
    Returns standardized MAC (xx:xx:xx:xx:xx:xx) or None if invalid.
    """
    if not mac:
        return None
        
    try:
        # Remove any non-hex characters
        mac = ''.join(c for c in mac if c.isalnum()).lower()
        
        # Validate length (12 hex chars = 6 bytes)
        if len(mac) != 12:
            return None
            
        # Validate hex characters only
        if not all(c in '0123456789abcdef' for c in mac):
            return None
            
        # Format as standard xx:xx:xx:xx:xx:xx
        return ':'.join([mac[i:i+2] for i in range(0, 12, 2)])
        
    except Exception:
        return None