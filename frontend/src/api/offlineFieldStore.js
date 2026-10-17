const DB_NAME = "ankurai-fieldwork";
const DB_VERSION = 1;
const NOTE_STORE = "pending-task-notes";
const SNAPSHOT_STORE = "field-snapshots";

function openDatabase() {
  if (!("indexedDB" in window)) return Promise.reject(new Error("Offline storage is unavailable."));
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(NOTE_STORE)) database.createObjectStore(NOTE_STORE, { keyPath: "task_id" });
      if (!database.objectStoreNames.contains(SNAPSHOT_STORE)) database.createObjectStore(SNAPSHOT_STORE, { keyPath: "key" });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function transact(storeName, mode, action) {
  return openDatabase().then((database) => new Promise((resolve, reject) => {
    const transaction = database.transaction(storeName, mode);
    const request = action(transaction.objectStore(storeName));
    let result;
    request.onsuccess = () => { result = request.result; };
    request.onerror = () => { result = request.error; };
    transaction.onerror = () => { result = transaction.error; };
    transaction.onabort = () => {
      database.close();
      reject(result || transaction.error || new Error("Offline storage transaction failed."));
    };
    transaction.oncomplete = () => {
      database.close();
      resolve(result);
    };
  }));
}

export function savePendingTaskNote(taskId, notes, status) {
  return transact(NOTE_STORE, "readwrite", (store) => store.put({ task_id: Number(taskId), notes, status, updated_at: new Date().toISOString() }));
}

export function getPendingTaskNotes() {
  return transact(NOTE_STORE, "readonly", (store) => store.getAll());
}

export function removePendingTaskNote(taskId) {
  return transact(NOTE_STORE, "readwrite", (store) => store.delete(Number(taskId)));
}

export function saveFieldSnapshot(key, data) {
  return transact(SNAPSHOT_STORE, "readwrite", (store) => store.put({ key, data, saved_at: new Date().toISOString() }));
}

export function getFieldSnapshot(key) {
  return transact(SNAPSHOT_STORE, "readonly", (store) => store.get(key));
}
