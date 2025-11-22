import http.server
import socketserver
import urllib.parse
import webbrowser
import secrets
import string
import hashlib
import base64
import requests
import json
import threading

# ================= CONFIGURAÇÕES =================
CLIENT_KEY = "sbawigbnl1gvxb316z"  # seu client_key TikTok
CLIENT_SECRET = "T2zK2Q1wL8s1oITTizM7iOuwosmEBv8z" # seu client_secret TikTok
REDIRECT_URI = "http://localhost:5678/rest/oauth2-credential/callback"  # deve estar registrado no TikTok
SCOPES = "user.info.basic,user.info.profile,user.info.stats,video.list,video.upload"
PORT = 5678
# ==================================================

def generate_pkce_pair():
    code_verifier = ''.join(secrets.choice(string.ascii_letters + string.digits + "-._~") for _ in range(64))
    code_challenge = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).rstrip(b'=').decode('ascii')
    return code_verifier, code_challenge

def generate_state(length=16):
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))

def run_server(CODE_VERIFIER, STATE):

    class TikTokOAuthHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            parsed_path = urllib.parse.urlparse(self.path)
            if parsed_path.path != '/callback':
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not Found")
                return

            query = urllib.parse.parse_qs(parsed_path.query)
            code = query.get("code", [None])[0]
            state_received = query.get("state", [None])[0]

            if not code:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing code parameter")
                return

            if state_received != STATE:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Invalid state parameter")
                return

            data = {
                "client_key": CLIENT_KEY,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": REDIRECT_URI,
                "code_verifier": CODE_VERIFIER
            }

            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            response = requests.post("https://open.tiktokapis.com/v2/oauth/token/", data=data, headers=headers)

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()

            if response.status_code != 200:
                self.wfile.write(f"Erro na troca do token: {response.text}".encode())
            else:
                token_data = response.json()
                self.wfile.write("<h2>✅ Login bem-sucedido!</h2>".encode('utf-8'))
                self.wfile.write(b"<pre>")
                self.wfile.write(json.dumps(token_data, indent=4).encode())
                self.wfile.write(b"</pre>")

            print("\nTokens recebidos:", response.json())
            print("Fechando servidor...")
            threading.Thread(target=httpd.shutdown).start()

    with socketserver.TCPServer(("", PORT), TikTokOAuthHandler) as httpd:
        print(f"Servidor ouvindo em http://localhost:{PORT}/callback ...")
        httpd.serve_forever()

def main():
    CODE_VERIFIER, CODE_CHALLENGE = generate_pkce_pair()
    STATE = generate_state()

    params = {
        "client_key": CLIENT_KEY,
        "response_type": "code",
        "scope": SCOPES,
        "redirect_uri": REDIRECT_URI,
        "state": STATE,
        "code_challenge": CODE_CHALLENGE,
        "code_challenge_method": "S256"
    }

    auth_url = "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode(params)
    print("Abra este link no navegador para autorizar o app:\n", auth_url)
    webbrowser.open(auth_url)

    run_server(CODE_VERIFIER, STATE)

if __name__ == "__main__":
    main()
