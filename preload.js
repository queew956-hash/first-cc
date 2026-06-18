const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('pomodoroAPI', {
  sendNotification: (title, body) => ipcRenderer.invoke('send-notification', { title, body }),
  toggleAlwaysOnTop: () => ipcRenderer.invoke('toggle-always-on-top'),
});
