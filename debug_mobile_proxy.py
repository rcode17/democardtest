import urllib.request

USER = "f0598b258d0d3f429dfe"
PASS = "00522fa86bebdbc1"

# DataImpulse mobile proxy - puerto 823 con parametro type.mobile
configs = [
    # Residencial normal (control)
    f"http://{USER}__cr.es:{PASS}@gw.dataimpulse.com:823",
    # Mobile con parametro
    f"http://{USER}__cr.es;type.mobile:{PASS}@gw.dataimpulse.com:823",
    # Mobile puerto diferente
    f"http://{USER}__cr.es:{PASS}@gw.dataimpulse.com:824",
    # Sin country, solo mobile
    f"http://{USER}__type.mobile:{PASS}@gw.dataimpulse.com:823",
]

labels = [
    "Residencial ES (control)",
    "Mobile ES puerto 823",
    "Mobile ES puerto 824",
    "Mobile sin country",
]

for label, proxy_url in zip(labels, configs):
    try:
        proxy_handler = urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url})
        opener = urllib.request.build_opener(proxy_handler)
        resp = opener.open('http://api.ipify.org', timeout=10)
        ip = resp.read().decode()
        # Verificar si es IP móvil
        resp2 = opener.open(f'http://ip-api.com/json/{ip}?fields=status,isp,org,mobile', timeout=10)
        info = resp2.read().decode()
        print(f"✅ {label}: IP={ip} | {info[:80]}")
    except Exception as e:
        print(f"❌ {label}: {str(e)[:60]}")
