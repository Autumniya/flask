from app import app

if __name__ == '__main__':
    initialize_db()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
