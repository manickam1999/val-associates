const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electron', {
  getPorts: () => {
    ipcRenderer.send('get-ports');
    return new Promise((resolve) => {
      ipcRenderer.once('ports', (event, ports) => {
        resolve(ports);
      });
    });
  }
});
