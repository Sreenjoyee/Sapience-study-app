from studyapp import app,os
port = int(os.environ.get("PORT", 5000))

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=port)