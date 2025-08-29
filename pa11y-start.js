const { spawn } = require('child_process');
const net = require('net');

// Allow extra time for the application to start in slower environments
const APP_PORT = 8000;
const WAIT_TIMEOUT_MS = 60000; // 60 seconds

let server;
async function waitForPort(port, timeoutMs) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    (function check() {
      const socket = net.connect(port, '127.0.0.1', () => {
        socket.end();
        resolve();
      });
      socket.on('error', () => {
        socket.destroy();
        if (Date.now() - start > timeoutMs) {
          reject(new Error('Timed out waiting for port ' + port));
        } else {
          setTimeout(check, 100);
        }
      });
    })();
  });
}
module.exports = async () => {
  if (!server) {
    server = spawn('python', ['start_app.py', '--skip-db-migrations'], {
      stdio: 'inherit',
    });
    process.on('exit', () => {
      if (server) server.kill();
    });
    await waitForPort(APP_PORT, WAIT_TIMEOUT_MS);
  }
};
