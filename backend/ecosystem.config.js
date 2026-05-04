module.exports = {
  apps: [
    {
      name: "fonus-backend",
      script: "uvicorn",
      args: "main:app --host 0.0.0.0 --port 8000",
      interpreter: "...\\.venv\\Scripts\\python.exe",
      cwd: "D:\\ai coach fonus\\code_test_fonus\\fonus\\backend",
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
      env: {
        PYTHONPATH: "D:\\ai coach fonus\\code_test_fonus\\fonus"
      }
    }
  ]
}