import os
from flask import Flask, jsonify
from dbconnection import DatabaseClient

def create_app() -> Flask:
    app = Flask(__name__)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.getenv(
        "DB_CONFIG_PATH",
        os.path.join(base_dir, "config", "database.config"),
    )

    # One pool per process
    db = DatabaseClient.from_properties(config_path)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.get("/db-test")
    def db_test():
        try:
            rows = db.execute_select("SELECT sysdate AS server_time FROM dual")
            return jsonify({"success": True, "result": rows}), 200
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.get("/db-sample-query")
    def sample():
        try:
            sql = """
                SELECT DOCUMENT_ID, DOCUMENT_NAME
                FROM appsawb.DOCUMANTRA_DOCS
                FETCH FIRST 5 ROWS ONLY
            """
            rows = db.execute_select(sql)
            return jsonify(rows), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
