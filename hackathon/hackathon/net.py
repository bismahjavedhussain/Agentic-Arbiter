"""DNS-over-HTTPS override: the local router DNS is refusing many hosts, so we
resolve names through Cloudflare (1.1.1.1) and patch socket.getaddrinfo to use the
resolved IPs. Import this module before making any requests."""
import socket, json, urllib.request, ssl

_cache = {}
_orig = socket.getaddrinfo

def _doh(host):
    if host in _cache:
        return _cache[host]
    try:
        req = urllib.request.Request(
            f"https://1.1.1.1/dns-query?name={host}&type=A",
            headers={"accept": "application/dns-json"})
        ctx = ssl.create_default_context()
        data = json.load(urllib.request.urlopen(req, timeout=15, context=ctx))
        ips = [a["data"] for a in data.get("Answer", []) if a.get("type") == 1]
        _cache[host] = ips[0] if ips else None
    except Exception:
        _cache[host] = None
    return _cache[host]

def _patched(host, *args, **kwargs):
    try:
        return _orig(host, *args, **kwargs)          # try the OS resolver first
    except socket.gaierror:
        ip = _doh(host) if isinstance(host, str) else None
        if ip:
            return _orig(ip, *args, **kwargs)
        raise

socket.getaddrinfo = _patched
