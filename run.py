from app import create_app
from app.network import get_lan_ip
from pathlib import Path

app = create_app()

if __name__ == "__main__":
    port = 5000
    lan_ip = get_lan_ip()
    project_dir = Path(__file__).resolve().parent
    cert_file = project_dir / "certs" / "local-cert.pem"
    key_file = project_dir / "certs" / "local-key.pem"
    ssl_context = (str(cert_file), str(key_file)) if cert_file.exists() and key_file.exists() else None
    scheme = "https" if ssl_context else "http"

    print(f"BioFace neste computador: {scheme}://localhost:{port}")
    if lan_ip != "127.0.0.1":
        print(f"BioFace na rede local: {scheme}://{lan_ip}:{port}/")
    else:
        print("Não consegui detectar o IP da rede. Consulte o IP IPv4 do computador para abrir no celular.")
    if not ssl_context:
        print("HTTPS não configurado. Execute .\\scripts\\setup_https.ps1 e reinicie para habilitar a webcam pela rede.")
    app.run(host="0.0.0.0", port=port, debug=False, ssl_context=ssl_context)
