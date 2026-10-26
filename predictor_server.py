import json
import numpy as np
import xgboost as xgb
from http.server import BaseHTTPRequestHandler, HTTPServer

MODEL = "/home/hadiya/fyp/xgb_mininet4.json"
FEATURES = ["pkts_per_s", "bytes_per_s", "avg_pkt_size"]

bst = xgb.Booster()
bst.load_model(MODEL)

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        rows = json.loads(self.rfile.read(n))["rows"]
        X = np.array(rows, dtype=float).reshape(-1, len(FEATURES))
        probs = bst.predict(xgb.DMatrix(X, feature_names=FEATURES),
                            validate_features=False)
        out = json.dumps({"probs": [float(p) for p in probs],
                          "preds": [int(p >= 0.5) for p in probs]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *args):
        pass

print("predictor ready on 127.0.0.1:5001, features:", FEATURES)
HTTPServer(("127.0.0.1", 5001), Handler).serve_forever()
